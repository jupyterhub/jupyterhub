"""API for JupyterHub's proxy.

Route Specification:

- A routespec is a URI (excluding scheme), e.g.
  'host.name/path/' for host-based routing or '/path/' for default routing.
- Route paths should be normalized to always start and end with `/`
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

from collections import namedtuple
import json
import os
from subprocess import Popen
import time
from urllib.parse import quote, urlparse

from tornado import gen
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.ioloop import PeriodicCallback


from traitlets import (
    Any, Bool, Instance, Integer, Unicode,
    default,
)
from jupyterhub.traitlets import Command

from traitlets.config import LoggingConfigurable
from .objects import Server
from .orm import Service, User
from . import utils
from .utils import url_path_join


class Proxy(LoggingConfigurable):
    """Base class for configurable proxies that JupyterHub can use."""

    db = Any()
    app = Any()
    hub = Any()
    public_url = Unicode()
    ssl_key = Unicode()
    ssl_cert = Unicode()
    host_routing = Bool()

    should_start = Bool(True, config=True,
                        help="""Should the Hub start the proxy.

        If True, the Hub will start the proxy and stop it.
        Set to False if the proxy is managed externally,
        such as by systemd, docker, or another service manager.
        """)

    def start(self):
        """Start the proxy.

        Will be called during startup if should_start is True.
        """

    def stop(self):
        """Stop the proxy.

        Will be called during teardown if should_start is True.
        """
    
    def validate_routespec(self, routespec):
        """Validate a routespec
        
        - Checks host value vs host-based routing.
        - Ensures trailing slash on path.
        """
        # check host routing
        host_route = not routespec.startswith('/')
        if host_route and not self.host_routing:
            raise ValueError("Cannot add host-based route %r, not using host-routing" % routespec)
        if self.host_routing and not host_route:
            raise ValueError("Cannot add route without host %r, using host-routing" % routespec)
        # add trailing slash
        if not routespec.endswith('/'):
            return routespec + '/'
        else:
            return routespec

    @gen.coroutine
    def add_route(self, routespec, target, data):
        """Add a route to the proxy.

        Args:
            routespec (str): A URI (excluding scheme) for which this route will be matched,
                e.g. host.name/path/
            target (str): A URL that will be the target of this route.
            data (dict): A JSONable dict that will be associated with this route, and will
                be returned when retrieving information about this route.

        Will raise an appropriate Exception (FIXME: find what?) if the route could
        not be added.

        The proxy implementation should also have a way to associate the fact that a
        route came from JupyterHub.
        """
        pass

    @gen.coroutine
    def delete_route(self, routespec):
        """Delete a route with a given routespec if it exists."""
        pass

    @gen.coroutine
    def get_all_routes(self):
        """Fetch and return all the routes associated by JupyterHub from the
        proxy.

        Should return a dictionary of routes, where the keys are
        routespecs and each value is a dict of the form::

          {
            'routespec': the route specification
            'target': the target host for this route
            'data': the attached data dict for this route (as specified in add_route)
          }
        that would be returned by
        `get_route(routespec)`.
        """
        pass

    @gen.coroutine
    def get_route(self, routespec):
        """Return the route info for a given routespec.

        Args:
            routespec (str): A URI that was used to add this route,
                e.g. `host.tld/path/`

        Returns:
            result (dict): with the following keys:
                `routespec`: The normalized route specification passed in to add_route
                `target`: The target for this route
                `data`: The arbitrary data that was passed in by JupyterHub when adding this
                        route.
            None: if there are no routes matching the given routespec
        """
        # default implementation relies on get_all_routes
        routespec = self.validate_routespec(routespec)
        routes = yield self.get_all_routes()
        return routes.get(routespec)

    # Most basic implementers must only implement above methods

    @gen.coroutine
    def add_service(self, service, client=None):
        """Add a service's server to the proxy table."""
        if not service.server:
            raise RuntimeError(
                "Service %s does not have an http endpoint to add to the proxy.", service.name)

        self.log.info("Adding service %s to proxy %s => %s",
                      service.name, service.proxy_spec, service.server.host,
                      )

        yield self.add_route(
            service.proxy_spec,
            service.server.host,
            {'service': service.name}
        )

    @gen.coroutine
    def delete_service(self, service, client=None):
        """Remove a service's server from the proxy table."""
        self.log.info("Removing service %s from proxy", service.name)
        yield self.delete_route(service.proxy_spec)

    @gen.coroutine
    def add_user(self, user, client=None):
        """Add a user's server to the proxy table."""
        self.log.info("Adding user %s to proxy %s => %s",
                      user.name, user.proxy_spec, user.server.host,
                      )

        if user.spawn_pending:
            raise RuntimeError(
                "User %s's spawn is pending, shouldn't be added to the proxy yet!", user.name)

        yield self.add_route(
            user.proxy_spec,
            user.server.host,
            {'user': user.name}
        )

    @gen.coroutine
    def delete_user(self, user):
        """Remove a user's server from the proxy table."""
        self.log.info("Removing user %s from proxy", user.name)
        yield self.delete_route(user.proxy_spec)

    @gen.coroutine
    def add_all_services(self, service_dict):
        """Update the proxy table from the database.

        Used when loading up a new proxy.
        """
        db = self.db
        futures = []
        for orm_service in db.query(Service):
            service = service_dict[orm_service.name]
            if service.server:
                futures.append(self.add_service(service))
        # wait after submitting them all
        for f in futures:
            yield f

    @gen.coroutine
    def add_all_users(self, user_dict):
        """Update the proxy table from the database.

        Used when loading up a new proxy.
        """
        db = self.db
        futures = []
        for orm_user in db.query(User):
            user = user_dict[orm_user]
            if user.running:
                futures.append(self.add_user(user))
        # wait after submitting them all
        for f in futures:
            yield f

    @gen.coroutine
    def check_routes(self, user_dict, service_dict, routes=None):
        """Check that all users are properly routed on the proxy."""
        if not routes:
            routes = yield self.get_all_routes()

        user_routes = {r['data']['user'] for r in routes.values() if 'user' in r['data']}
        futures = []
        db = self.db
        for orm_user in db.query(User):
            user = user_dict[orm_user]
            if user.running:
                if user.name not in user_routes:
                    self.log.warning(
                        "Adding missing route for %s (%s)", user.name, user.server)
                    futures.append(self.add_user(user))
            else:
                # User not running, make sure it's not in the table
                if user.name in user_routes:
                    self.log.warning(
                        "Removing route for not running %s", user.name)
                    futures.append(self.delete_user(user))

        # check service routes
        service_routes = {r['data']['service']
                          for r in routes.values() if 'service' in r['data']}
        for orm_service in db.query(Service).filter(
                Service.server is not None):
            service = service_dict[orm_service.name]
            if service.server is None:
                # This should never be True, but seems to be on rare occasion.
                # catch filter bug, either in sqlalchemy or my understanding of
                # its behavior
                self.log.error(
                    "Service %s has no server, but wasn't filtered out.", service)
                continue
            if service.name not in service_routes:
                self.log.warning("Adding missing route for %s (%s)",
                                 service.name, service.server)
                futures.append(self.add_service(service))
        for f in futures:
            yield f

    @gen.coroutine
    def restore_routes(self):
        self.log.info("Setting up routes on new proxy")
        yield self.add_all_users(self.app.users)
        yield self.add_all_services(self.app.services)
        self.log.info("New proxy back up and good to go")


class ConfigurableHTTPProxy(Proxy):
    """Proxy implementation for the default configurable-http-proxy."""

    proxy_process = Any()
    client = Instance(AsyncHTTPClient, ())

    debug = Bool(False, help="Add debug-level logging to the Proxy", config=True)
    auth_token = Unicode(
        help="""The Proxy Auth token.

        Loaded from the CONFIGPROXY_AUTH_TOKEN env variable by default.
        """,
    ).tag(config=True)
    check_running_interval = Integer(5, config=True)

    @default('auth_token')
    def _auth_token_default(self):
        token = os.environ.get('CONFIGPROXY_AUTH_TOKEN', None)
        if not token:
            self.log.warning('\n'.join([
                "",
                "Generating CONFIGPROXY_AUTH_TOKEN. Restarting the Hub will require restarting the proxy.",
                "Set CONFIGPROXY_AUTH_TOKEN env or JupyterHub.proxy_auth_token config to avoid this message.",
                "",
            ]))
            token = utils.new_token()
        return token

    api_url = Unicode('http://127.0.0.1:8001', config=True,
                      help="""The ip (or hostname) of the proxy's API endpoint"""
                      )
    command = Command('configurable-http-proxy', config=True,
                      help="""The command to start the proxy"""
                      )

    @gen.coroutine
    def start(self):
        public_server = Server.from_url(self.public_url)
        api_server = Server.from_url(self.api_url)
        env = os.environ.copy()
        env['CONFIGPROXY_AUTH_TOKEN'] = self.auth_token
        cmd = self.command + [
            '--ip', public_server.ip,
            '--port', str(public_server.port),
            '--api-ip', api_server.ip,
            '--api-port', str(api_server.port),
            '--default-target', self.hub.host,
            '--error-target', url_path_join(self.hub.url, 'error'),
        ]
        if self.app.subdomain_host:
            cmd.append('--host-routing')
        if self.debug:
            cmd.extend(['--log-level', 'debug'])
        if self.ssl_key:
            cmd.extend(['--ssl-key', self.ssl_key])
        if self.ssl_cert:
            cmd.extend(['--ssl-cert', self.ssl_cert])
        if self.app.statsd_host:
            cmd.extend([
                '--statsd-host', self.app.statsd_host,
                '--statsd-port', str(self.app.statsd_port),
                '--statsd-prefix', self.app.statsd_prefix + '.chp'
            ])
        # Warn if SSL is not used
        if ' --ssl' not in ' '.join(cmd):
            self.log.warning("Running JupyterHub without SSL."
                             "  I hope there is SSL termination happening somewhere else...")
        self.log.info("Starting proxy @ %s", public_server.bind_url)
        self.log.debug("Proxy cmd: %s", cmd)
        try:
            self.proxy_process = Popen(cmd, env=env, start_new_session=True)
        except FileNotFoundError as e:
            self.log.error(
                "Failed to find proxy %r\n"
                "The proxy can be installed with `npm install -g configurable-http-proxy`"
                % self.cmd
            )
            self.exit(1)

        def _check_process():
            status = self.proxy_process.poll()
            if status is not None:
                e = RuntimeError(
                    "Proxy failed to start with exit code %i" % status)
                # py2-compatible `raise e from None`
                e.__cause__ = None
                raise e

        for server in (public_server, api_server):
            for i in range(10):
                _check_process()
                try:
                    yield server.wait_up(1)
                except TimeoutError:
                    continue
                else:
                    break
            yield server.wait_up(1)
        time.sleep(1)
        _check_process()
        self.log.debug("Proxy started and appears to be up")
        pc = PeriodicCallback(self.check_running, 1e3 * self.check_running_interval)
        pc.start()

    def stop(self):
        self.log.info("Cleaning up proxy[%i]...", self.proxy_process.pid)
        if self.proxy_process.poll() is None:
            try:
                self.proxy_process.terminate()
            except Exception as e:
                self.log.error("Failed to terminate proxy process: %s", e)

    @gen.coroutine
    def check_running(self):
        """Check if the proxy is still running"""
        if self.proxy_process.poll() is None:
            return
        self.log.error("Proxy stopped with exit code %r",
                       'unknown' if self.proxy_process is None else self.proxy_process.poll()
                       )
        yield self.start()
        yield self.restore_routes()

    def _routespec_to_chp_path(self, routespec):
        """Turn a routespec into a CHP API path

        For host-based routing, CHP uses the host as the first path segment.
        """
        path = self.validate_routespec(routespec)
        # CHP always wants to start with /
        if not path.startswith('/'):
            path = path + '/'
        # BUG: CHP doesn't seem to like trailing slashes on some endpoints (DELETE)
        if path != '/' and path.endswith('/'):
            path = path.rstrip('/')
        return path

    def _routespec_from_chp_path(self, chp_path):
        """Turn a CHP route into a route spec
        
        In the JSON API, CHP route keys are unescaped,
        so re-escape them to raw URLs and ensure slashes are in the right places.
        """
        # chp stores routes in unescaped form.
        # restore escaped-form we created it with.
        routespec = quote(chp_path, safe='@/')
        if self.host_routing:
            # host routes don't start with /
            routespec = routespec.lstrip('/')
        # all routes should end with /
        if not routespec.endswith('/'):
            routespec = routespec + '/'
        return routespec

    def api_request(self, path, method='GET', body=None, client=None):
        """Make an authenticated API request of the proxy."""
        client = client or AsyncHTTPClient()
        url = url_path_join(self.api_url, 'api/routes', path)

        if isinstance(body, dict):
            body = json.dumps(body)
        self.log.debug("Proxy: Fetching %s %s", method, url)
        req = HTTPRequest(url,
                          method=method,
                          headers={'Authorization': 'token {}'.format(
                              self.auth_token)},
                          body=body,
                          )

        return client.fetch(req)

    def add_route(self, routespec, target, data=None):
        body = data or {}
        body['target'] = target
        path = self._routespec_to_chp_path(routespec)
        return self.api_request(path,
                                method='POST',
                                body=body,
                                )

    def delete_route(self, routespec):
        path = self._routespec_to_chp_path(routespec)
        return self.api_request(path, method='DELETE')

    def _reformat_routespec(self, routespec, chp_data):
        """Reformat CHP data format to JupyterHub's proxy API."""
        target = chp_data.pop('target')
        return {
            'routespec': routespec,
            'target': target,
            'data': chp_data,
        }
    
    @gen.coroutine
    def get_all_routes(self, client=None):
        """Fetch the proxy's routes."""
        resp = yield self.api_request('', client=client)
        chp_routes = json.loads(resp.body.decode('utf8', 'replace'))
        all_routes = {}
        for chp_path, chp_data in chp_routes.items():
            routespec = self._routespec_from_chp_path(chp_path)
            all_routes[routespec] = self._reformat_routespec(
                routespec, chp_data)
        return all_routes
