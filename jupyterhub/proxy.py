"""API for JupyterHub's proxy.

Custom proxy implementations can subclass :class:`Proxy`
and register in JupyterHub config:

.. sourcecode:: python

    from mymodule import MyProxy
    c.JupyterHub.proxy_class = MyProxy

Route Specification:

- A routespec is a URL prefix ([host]/path/), e.g.
  'host.tld/path/' for host-based routing or '/path/' for default routing.
- Route paths should be normalized to always start and end with '/'
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import json
import os
from subprocess import Popen
from urllib.parse import quote

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
    """Base class for configurable proxies that JupyterHub can use.

    A proxy implementation should subclass this and must define the following methods:

    - :meth:`.get_all_routes` return a dictionary of all JupyterHub-related routes
    - :meth:`.add_route` adds a route
    - :meth:`.delete_route` deletes a route

    In addition to these, the following method(s) may need to be implemented:

    - :meth:`.start` start the proxy, if it should be launched by the Hub
      instead of externally managed.
      If the proxy is externally managed, it should set :attr:`should_start` to False.
    - :meth:`.stop` stop the proxy. Only used if :meth:`.start` is also used.

    And the following method(s) are optional, but can be provided:

    - :meth:`.get_route` gets a single route.
      There is a default implementation that extracts data from :meth:`.get_all_routes`,
      but implementations may choose to provide a more efficient implementation
      of fetching a single route.
    """

    db_factory = Any()
    @property
    def db(self):
        return self.db_factory()

    app = Any()
    hub = Any()
    public_url = Unicode()
    ssl_key = Unicode()
    ssl_cert = Unicode()
    host_routing = Bool()

    should_start = Bool(True, config=True,
                        help="""Should the Hub start the proxy

        If True, the Hub will start the proxy and stop it.
        Set to False if the proxy is managed externally,
        such as by systemd, docker, or another service manager.
        """)

    def start(self):
        """Start the proxy.

        Will be called during startup if should_start is True.

        **Subclasses must define this method**
        if the proxy is to be started by the Hub
        """

    def stop(self):
        """Stop the proxy.

        Will be called during teardown if should_start is True.

        **Subclasses must define this method** 
        if the proxy is to be started by the Hub
        """
    
    def validate_routespec(self, routespec):
        """Validate a routespec
        
        - Checks host value vs host-based routing.
        - Ensures trailing slash on path.
        """
        if routespec == '/':
            # / is the default route.
            # don't check host-based routing
            return routespec
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

        **Subclasses must define this method**

        Args:
            routespec (str): A URL prefix ([host]/path/) for which this route will be matched,
                e.g. host.name/path/
            target (str): A full URL that will be the target of this route.
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
        """Delete a route with a given routespec if it exists.
        
        **Subclasses must define this method**
        """
        pass

    @gen.coroutine
    def get_all_routes(self):
        """Fetch and return all the routes associated by JupyterHub from the
        proxy.

        **Subclasses must define this method**

        Should return a dictionary of routes, where the keys are
        routespecs and each value is a dict of the form::

          {
            'routespec': the route specification ([host]/path/)
            'target': the target host URL (proto://host) for this route
            'data': the attached data dict for this route (as specified in add_route)
          }
        """
        pass

    @gen.coroutine
    def get_route(self, routespec):
        """Return the route info for a given routespec.

        Args:
            routespec (str):
                A URI that was used to add this route,
                e.g. `host.tld/path/`

        Returns:
            result (dict):
                dict with the following keys::
        
                'routespec': The normalized route specification passed in to add_route
                    ([host]/path/)
                'target': The target host for this route (proto://host)
                'data': The arbitrary data dict that was passed in by JupyterHub when adding this
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
    def add_user(self, user, server_name='', client=None):
        """Add a user's server to the proxy table."""
        spawner = user.spawners[server_name]
        self.log.info("Adding user %s to proxy %s => %s",
                      user.name, spawner.proxy_spec, spawner.server.host,
                      )

        if spawner.pending and spawner.pending != 'spawn':
            raise RuntimeError(
                "%s is pending %s, shouldn't be added to the proxy yet!" % (spawner._log_name, spawner.pending)
            )

        yield self.add_route(
            spawner.proxy_spec,
            spawner.server.host,
            {
                'user': user.name,
                'server_name': server_name,
            }
        )

    @gen.coroutine
    def delete_user(self, user, server_name=''):
        """Remove a user's server from the proxy table."""
        routespec = user.proxy_spec
        if server_name:
            routespec = url_path_join(user.proxy_spec, server_name, '/')
        self.log.info("Removing user %s from proxy (%s)", user.name, routespec)
        yield self.delete_route(routespec)

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
            for name, spawner in user.spawners.items():
                if spawner.ready:
                    futures.append(self.add_user(user, name))
        # wait after submitting them all
        for f in futures:
            yield f

    @gen.coroutine
    def check_routes(self, user_dict, service_dict, routes=None):
        """Check that all users are properly routed on the proxy."""
        if not routes:
            routes = yield self.get_all_routes()

        user_routes = {path for path, r in routes.items() if 'user' in r['data']}
        futures = []
        db = self.db

        good_routes = {'/'}

        hub = self.app.hub
        if '/' not in routes:
            self.log.warning("Adding missing default route")
            futures.append(self.add_hub_route(hub))
        else:
            route = routes['/']
            if route['target'] != hub.host:
                self.log.warning("Updating default route %s → %s", route['target'], hub.host)
                futures.append(self.add_hub_route(hub))

        for orm_user in db.query(User):
            user = user_dict[orm_user]
            for name, spawner in user.spawners.items():
                if spawner.ready:
                    spec = spawner.proxy_spec
                    good_routes.add(spec)
                    if spec not in user_routes:
                        self.log.warning(
                            "Adding missing route for %s (%s)", spec, spawner.server)
                        futures.append(self.add_user(user, name))
                    else:
                        route = routes[spec]
                        if route['target'] != spawner.server.host:
                            self.log.warning(
                                "Updating route for %s (%s → %s)",
                                spec, route['target'], spawner.server,
                            )
                            futures.append(self.add_user(user, name))
                elif spawner._spawn_pending:
                    good_routes.add(spawner.proxy_spec)

        # check service routes
        service_routes = {r['data']['service']: r
                          for r in routes.values() if 'service' in r['data']}
        for orm_service in db.query(Service).filter(Service.server != None):
            service = service_dict[orm_service.name]
            if service.server is None:
                # This should never be True, but seems to be on rare occasion.
                # catch filter bug, either in sqlalchemy or my understanding of
                # its behavior
                self.log.error(
                    "Service %s has no server, but wasn't filtered out.", service)
                continue
            good_routes.add(service.proxy_spec)
            if service.name not in service_routes:
                self.log.warning("Adding missing route for %s (%s)",
                                 service.name, service.server)
                futures.append(self.add_service(service))
            else:
                route = service_routes[service.name]
                if route['target'] != service.server.host:
                    self.log.warning(
                        "Updating route for %s (%s → %s)",
                        route['routespec'], route['target'], spawner.server.host,
                    )
                    futures.append(self.add_service(service))

        # Now delete the routes that shouldn't be there
        for routespec in routes:
            if routespec not in good_routes:
                self.log.warning("Deleting stale route %s", routespec)
                futures.append(self.delete_route(routespec))

        for f in futures:
            yield f

    def add_hub_route(self, hub):
        """Add the default route for the Hub"""
        self.log.info("Adding default route for Hub: / => %s", hub.host)
        return self.add_route('/', self.hub.host, {'hub': True})

    @gen.coroutine
    def restore_routes(self):
        self.log.info("Setting up routes on new proxy")
        yield self.add_hub_route(self.app.hub)
        yield self.add_all_users(self.app.users)
        yield self.add_all_services(self.app._service_map)
        self.log.info("New proxy back up and good to go")


class ConfigurableHTTPProxy(Proxy):
    """Proxy implementation for the default configurable-http-proxy.

    This is the default proxy implementation
    for running the nodejs proxy `configurable-http-proxy`.

    If the proxy should not be run as a subprocess of the Hub,
    (e.g. in a separate container),
    set::
    
        c.ConfigurableHTTPProxy.should_start = False
    """

    proxy_process = Any()
    client = Instance(AsyncHTTPClient, ())

    debug = Bool(False, help="Add debug-level logging to the Proxy.", config=True)
    auth_token = Unicode(
        help="""The Proxy auth token

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
        shell = os.name == 'nt' 
        try:
            self.proxy_process = Popen(cmd, env=env, start_new_session=True, shell=shell)
        except FileNotFoundError as e:
            self.log.error(
                "Failed to find proxy %r\n"
                "The proxy can be installed with `npm install -g configurable-http-proxy`"
                % self.command
            )
            raise

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
            path = '/' + path
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

    def add_route(self, routespec, target, data):
        body = data or {}
        body['target'] = target
        body['jupyterhub'] = True
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
        chp_data.pop('jupyterhub')
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
            if 'jupyterhub' not in chp_data:
                # exclude routes not associated with JupyterHub
                self.log.debug("Omitting non-jupyterhub route %r", routespec)
                continue
            all_routes[routespec] = self._reformat_routespec(
                routespec, chp_data)
        return all_routes
