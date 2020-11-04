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
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio
import json
import os
import signal
import time
from functools import wraps
from subprocess import Popen
from urllib.parse import quote

from tornado import gen
from tornado.httpclient import AsyncHTTPClient
from tornado.httpclient import HTTPError
from tornado.httpclient import HTTPRequest
from tornado.ioloop import PeriodicCallback
from traitlets import Any
from traitlets import Bool
from traitlets import default
from traitlets import Instance
from traitlets import Integer
from traitlets import observe
from traitlets import Unicode
from traitlets.config import LoggingConfigurable

from . import utils
from .metrics import CHECK_ROUTES_DURATION_SECONDS
from .metrics import PROXY_POLL_DURATION_SECONDS
from .objects import Server
from .utils import exponential_backoff
from .utils import make_ssl_context
from .utils import url_path_join
from jupyterhub.traitlets import Command


def _one_at_a_time(method):
    """decorator to limit an async method to be called only once

    If multiple concurrent calls to this method are made,
    queue them instead of allowing them to be concurrently outstanding.
    """
    method._lock = asyncio.Lock()

    @wraps(method)
    async def locked_method(*args, **kwargs):
        async with method._lock:
            return await method(*args, **kwargs)

    return locked_method


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

    should_start = Bool(
        True,
        config=True,
        help="""Should the Hub start the proxy

        If True, the Hub will start the proxy and stop it.
        Set to False if the proxy is managed externally,
        such as by systemd, docker, or another service manager.
        """,
    )

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
            raise ValueError(
                "Cannot add host-based route %r, not using host-routing" % routespec
            )
        if self.host_routing and not host_route:
            raise ValueError(
                "Cannot add route without host %r, using host-routing" % routespec
            )
        # add trailing slash
        if not routespec.endswith('/'):
            return routespec + '/'
        else:
            return routespec

    async def add_route(self, routespec, target, data):
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

    async def delete_route(self, routespec):
        """Delete a route with a given routespec if it exists.

        **Subclasses must define this method**
        """
        pass

    async def get_all_routes(self):
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

    async def get_route(self, routespec):
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
        routes = await self.get_all_routes()
        return routes.get(routespec)

    # Most basic implementers must only implement above methods

    async def add_service(self, service, client=None):
        """Add a service's server to the proxy table."""
        if not service.server:
            raise RuntimeError(
                "Service %s does not have an http endpoint to add to the proxy.",
                service.name,
            )

        self.log.info(
            "Adding service %s to proxy %s => %s",
            service.name,
            service.proxy_spec,
            service.server.host,
        )

        await self.add_route(
            service.proxy_spec, service.server.host, {'service': service.name}
        )

    async def delete_service(self, service, client=None):
        """Remove a service's server from the proxy table."""
        self.log.info("Removing service %s from proxy", service.name)
        await self.delete_route(service.proxy_spec)

    async def add_user(self, user, server_name='', client=None):
        """Add a user's server to the proxy table."""
        spawner = user.spawners[server_name]
        self.log.info(
            "Adding user %s to proxy %s => %s",
            user.name,
            spawner.proxy_spec,
            spawner.server.host,
        )

        if spawner.pending and spawner.pending != 'spawn':
            raise RuntimeError(
                "%s is pending %s, shouldn't be added to the proxy yet!"
                % (spawner._log_name, spawner.pending)
            )

        await self.add_route(
            spawner.proxy_spec,
            spawner.server.host,
            {'user': user.name, 'server_name': server_name},
        )

    async def delete_user(self, user, server_name=''):
        """Remove a user's server from the proxy table."""
        routespec = user.proxy_spec
        if server_name:
            routespec = url_path_join(user.proxy_spec, server_name, '/')
        self.log.info("Removing user %s from proxy (%s)", user.name, routespec)
        await self.delete_route(routespec)

    async def add_all_services(self, service_dict):
        """Update the proxy table from the database.

        Used when loading up a new proxy.
        """
        futures = []
        for service in service_dict.values():
            if service.server:
                futures.append(self.add_service(service))
        # wait after submitting them all
        await gen.multi(futures)

    async def add_all_users(self, user_dict):
        """Update the proxy table from the database.

        Used when loading up a new proxy.
        """
        futures = []
        for user in user_dict.values():
            for name, spawner in user.spawners.items():
                if spawner.ready:
                    futures.append(self.add_user(user, name))
        # wait after submitting them all
        await gen.multi(futures)

    @_one_at_a_time
    async def check_routes(self, user_dict, service_dict, routes=None):
        """Check that all users are properly routed on the proxy."""
        start = time.perf_counter()  # timer starts here when user is created
        if not routes:
            self.log.debug("Fetching routes to check")
            routes = await self.get_all_routes()
        # log info-level that we are starting the route-checking
        # this may help diagnose performance issues,
        # as we are about
        self.log.info("Checking routes")

        user_routes = {path for path, r in routes.items() if 'user' in r['data']}
        futures = []

        good_routes = {self.app.hub.routespec}

        hub = self.hub
        if self.app.hub.routespec not in routes:
            futures.append(self.add_hub_route(hub))
        else:
            route = routes[self.app.hub.routespec]
            if route['target'] != hub.host:
                self.log.warning(
                    "Updating default route %s → %s", route['target'], hub.host
                )
                futures.append(self.add_hub_route(hub))

        for user in user_dict.values():
            for name, spawner in user.spawners.items():
                if spawner.ready:
                    spec = spawner.proxy_spec
                    good_routes.add(spec)
                    if spec not in user_routes:
                        self.log.warning(
                            "Adding missing route for %s (%s)", spec, spawner.server
                        )
                        futures.append(self.add_user(user, name))
                    else:
                        route = routes[spec]
                        if route['target'] != spawner.server.host:
                            self.log.warning(
                                "Updating route for %s (%s → %s)",
                                spec,
                                route['target'],
                                spawner.server,
                            )
                            futures.append(self.add_user(user, name))
                elif spawner.pending:
                    # don't consider routes stale if the spawner is in any pending event
                    # wait until after the pending state clears before taking any actions
                    # they could be pending deletion from the proxy!
                    good_routes.add(spawner.proxy_spec)

        # check service routes
        service_routes = {
            r['data']['service']: r for r in routes.values() if 'service' in r['data']
        }
        for service in service_dict.values():
            if service.server is None:
                continue
            good_routes.add(service.proxy_spec)
            if service.name not in service_routes:
                self.log.warning(
                    "Adding missing route for %s (%s)", service.name, service.server
                )
                futures.append(self.add_service(service))
            else:
                route = service_routes[service.name]
                if route['target'] != service.server.host:
                    self.log.warning(
                        "Updating route for %s (%s → %s)",
                        route['routespec'],
                        route['target'],
                        service.server.host,
                    )
                    futures.append(self.add_service(service))

        # Now delete the routes that shouldn't be there
        for routespec in routes:
            if routespec not in good_routes:
                self.log.warning("Deleting stale route %s", routespec)
                futures.append(self.delete_route(routespec))

        await gen.multi(futures)
        stop = time.perf_counter()  # timer stops here when user is deleted
        CHECK_ROUTES_DURATION_SECONDS.observe(stop - start)  # histogram metric

    def add_hub_route(self, hub):
        """Add the default route for the Hub"""
        self.log.info("Adding default route for Hub: %s => %s", hub.routespec, hub.host)
        return self.add_route(hub.routespec, self.hub.host, {'hub': True})

    async def restore_routes(self):
        self.log.info("Setting up routes on new proxy")
        await self.add_hub_route(self.app.hub)
        await self.add_all_users(self.app.users)
        await self.add_all_services(self.app._service_map)
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

    concurrency = Integer(
        10,
        config=True,
        help="""
        The number of requests allowed to be concurrently outstanding to the proxy

        Limiting this number avoids potential timeout errors
        by sending too many requests to update the proxy at once
        """,
    )
    semaphore = Any()

    @default('semaphore')
    def _default_semaphore(self):
        return asyncio.BoundedSemaphore(self.concurrency)

    @observe('concurrency')
    def _concurrency_changed(self, change):
        self.semaphore = asyncio.BoundedSemaphore(change.new)

    debug = Bool(False, help="Add debug-level logging to the Proxy.", config=True)
    auth_token = Unicode(
        help="""The Proxy auth token

        Loaded from the CONFIGPROXY_AUTH_TOKEN env variable by default.
        """
    ).tag(config=True)
    check_running_interval = Integer(5, config=True)

    @default('auth_token')
    def _auth_token_default(self):
        token = os.environ.get('CONFIGPROXY_AUTH_TOKEN', '')
        if self.should_start and not token:
            # generating tokens is fine if the Hub is starting the proxy
            self.log.info("Generating new CONFIGPROXY_AUTH_TOKEN")
            token = utils.new_token()
        return token

    api_url = Unicode(
        config=True, help="""The ip (or hostname) of the proxy's API endpoint"""
    )

    @default('api_url')
    def _api_url_default(self):
        url = '127.0.0.1:8001'
        proto = 'http'
        if self.app.internal_ssl:
            proto = 'https'

        return "{proto}://{url}".format(proto=proto, url=url)

    command = Command(
        'configurable-http-proxy',
        config=True,
        help="""The command to start the proxy""",
    )

    pid_file = Unicode(
        "jupyterhub-proxy.pid",
        config=True,
        help="File in which to write the PID of the proxy process.",
    )

    _check_running_callback = Any(
        help="PeriodicCallback to check if the proxy is running"
    )

    def _check_pid(self, pid):
        if os.name == 'nt':
            import psutil

            if not psutil.pid_exists(pid):
                raise ProcessLookupError
        else:
            os.kill(pid, 0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # check for required token if proxy is external
        if not self.auth_token and not self.should_start:
            raise ValueError(
                "%s.auth_token or CONFIGPROXY_AUTH_TOKEN env is required"
                " if Proxy.should_start is False" % self.__class__.__name__
            )

    def _check_previous_process(self):
        """Check if there's a process leftover and shut it down if so"""
        if not self.pid_file or not os.path.exists(self.pid_file):
            return
        pid_file = os.path.abspath(self.pid_file)
        self.log.warning("Found proxy pid file: %s", pid_file)
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
        except ValueError:
            self.log.warning("%s did not appear to contain a pid", pid_file)
            self._remove_pid_file()
            return

        try:
            self._check_pid(pid)
        except ProcessLookupError:
            self.log.warning("Proxy no longer running at pid=%s", pid)
            self._remove_pid_file()
            return

        # if we got here, CHP is still running
        self.log.warning("Proxy still running at pid=%s", pid)
        if os.name != 'nt':
            sig_list = [signal.SIGTERM] * 2 + [signal.SIGKILL]
        for i in range(3):
            try:
                if os.name == 'nt':
                    self._terminate_win(pid)
                else:
                    os.kill(pid, sig_list[i])
            except ProcessLookupError:
                break
            time.sleep(1)
            try:
                self._check_pid(pid)
            except ProcessLookupError:
                break

        try:
            self._check_pid(pid)
        except ProcessLookupError:
            self.log.warning("Stopped proxy at pid=%s", pid)
            self._remove_pid_file()
            return
        else:
            raise RuntimeError("Failed to stop proxy at pid=%s", pid)

    def _write_pid_file(self):
        """write pid for proxy to a file"""
        self.log.debug("Writing proxy pid file: %s", self.pid_file)
        with open(self.pid_file, "w") as f:
            f.write(str(self.proxy_process.pid))

    def _remove_pid_file(self):
        """Cleanup pid file for proxy after stopping"""
        if not self.pid_file:
            return
        self.log.debug("Removing proxy pid file %s", self.pid_file)
        try:
            os.remove(self.pid_file)
        except FileNotFoundError:
            self.log.debug("PID file %s already removed", self.pid_file)
            pass

    async def start(self):
        """Start the proxy process"""
        # check if there is a previous instance still around
        self._check_previous_process()

        # build the command to launch
        public_server = Server.from_url(self.public_url)
        api_server = Server.from_url(self.api_url)
        env = os.environ.copy()
        env['CONFIGPROXY_AUTH_TOKEN'] = self.auth_token
        cmd = self.command + [
            '--ip',
            public_server.ip,
            '--port',
            str(public_server.port),
            '--api-ip',
            api_server.ip,
            '--api-port',
            str(api_server.port),
            '--error-target',
            url_path_join(self.hub.url, 'error'),
        ]
        if self.app.subdomain_host:
            cmd.append('--host-routing')
        if self.debug:
            cmd.extend(['--log-level', 'debug'])
        if self.ssl_key:
            cmd.extend(['--ssl-key', self.ssl_key])
        if self.ssl_cert:
            cmd.extend(['--ssl-cert', self.ssl_cert])
        if self.app.internal_ssl:
            proxy_api = 'proxy-api'
            proxy_client = 'proxy-client'
            api_key = self.app.internal_proxy_certs[proxy_api]['keyfile']
            api_cert = self.app.internal_proxy_certs[proxy_api]['certfile']
            api_ca = self.app.internal_trust_bundles[proxy_api + '-ca']

            client_key = self.app.internal_proxy_certs[proxy_client]['keyfile']
            client_cert = self.app.internal_proxy_certs[proxy_client]['certfile']
            client_ca = self.app.internal_trust_bundles[proxy_client + '-ca']

            cmd.extend(['--api-ssl-key', api_key])
            cmd.extend(['--api-ssl-cert', api_cert])
            cmd.extend(['--api-ssl-ca', api_ca])
            cmd.extend(['--api-ssl-request-cert'])
            cmd.extend(['--api-ssl-reject-unauthorized'])

            cmd.extend(['--client-ssl-key', client_key])
            cmd.extend(['--client-ssl-cert', client_cert])
            cmd.extend(['--client-ssl-ca', client_ca])
            cmd.extend(['--client-ssl-request-cert'])
            cmd.extend(['--client-ssl-reject-unauthorized'])
        if self.app.statsd_host:
            cmd.extend(
                [
                    '--statsd-host',
                    self.app.statsd_host,
                    '--statsd-port',
                    str(self.app.statsd_port),
                    '--statsd-prefix',
                    self.app.statsd_prefix + '.chp',
                ]
            )
        # Warn if SSL is not used
        if ' --ssl' not in ' '.join(cmd):
            self.log.warning(
                "Running JupyterHub without SSL."
                "  I hope there is SSL termination happening somewhere else..."
            )
        self.log.info("Starting proxy @ %s", public_server.bind_url)
        self.log.debug("Proxy cmd: %s", cmd)
        shell = os.name == 'nt'
        try:
            self.proxy_process = Popen(
                cmd, env=env, start_new_session=True, shell=shell
            )
        except FileNotFoundError as e:
            self.log.error(
                "Failed to find proxy %r\n"
                "The proxy can be installed with `npm install -g configurable-http-proxy`."
                "To install `npm`, install nodejs which includes `npm`."
                "If you see an `EACCES` error or permissions error, refer to the `npm` "
                "documentation on How To Prevent Permissions Errors." % self.command
            )
            raise

        self._write_pid_file()

        def _check_process():
            status = self.proxy_process.poll()
            if status is not None:
                e = RuntimeError("Proxy failed to start with exit code %i" % status)
                raise e from None

        for server in (public_server, api_server):
            for i in range(10):
                _check_process()
                try:
                    await server.wait_up(1)
                except TimeoutError:
                    continue
                else:
                    break
            await server.wait_up(1)
        _check_process()
        self.log.debug("Proxy started and appears to be up")
        pc = PeriodicCallback(self.check_running, 1e3 * self.check_running_interval)
        self._check_running_callback = pc
        pc.start()

    def _terminate_win(self, pid):
        # On Windows we spawned a shell on Popen, so we need to
        # terminate all child processes as well
        import psutil

        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        for child in children:
            child.kill()
        psutil.wait_procs(children, timeout=5)

    def _terminate(self):
        """Terminate our process"""
        if os.name == 'nt':
            self._terminate_win(self.proxy_process.pid)
        else:
            self.proxy_process.terminate()

    def stop(self):
        self.log.info("Cleaning up proxy[%i]...", self.proxy_process.pid)
        if self._check_running_callback is not None:
            self._check_running_callback.stop()
        if self.proxy_process.poll() is None:
            try:
                self._terminate()
            except Exception as e:
                self.log.error("Failed to terminate proxy process: %s", e)
        self._remove_pid_file()

    async def check_running(self):
        """Check if the proxy is still running"""
        if self.proxy_process.poll() is None:
            return
        self.log.error(
            "Proxy stopped with exit code %r",
            'unknown' if self.proxy_process is None else self.proxy_process.poll(),
        )
        self._remove_pid_file()
        await self.start()
        await self.restore_routes()

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
        routespec = quote(chp_path, safe='@/~')
        if self.host_routing:
            # host routes don't start with /
            routespec = routespec.lstrip('/')
        # all routes should end with /
        if not routespec.endswith('/'):
            routespec = routespec + '/'
        return routespec

    async def api_request(self, path, method='GET', body=None, client=None):
        """Make an authenticated API request of the proxy."""
        client = client or AsyncHTTPClient()
        url = url_path_join(self.api_url, 'api/routes', path)

        if isinstance(body, dict):
            body = json.dumps(body)
        self.log.debug("Proxy: Fetching %s %s", method, url)
        req = HTTPRequest(
            url,
            method=method,
            headers={'Authorization': 'token {}'.format(self.auth_token)},
            body=body,
            connect_timeout=3,  # default: 20s
            request_timeout=10,  # default: 20s
        )

        async def _wait_for_api_request():
            try:
                async with self.semaphore:
                    return await client.fetch(req)
            except HTTPError as e:
                # Retry on potentially transient errors in CHP, typically
                # numbered 500 and up. Note that CHP isn't able to emit 429
                # errors.
                if e.code >= 500:
                    self.log.warning(
                        "api_request to the proxy failed with status code {}, retrying...".format(
                            e.code
                        )
                    )
                    return False  # a falsy return value make exponential_backoff retry
                else:
                    self.log.error("api_request to proxy failed: {0}".format(e))
                    # An unhandled error here will help the hub invoke cleanup logic
                    raise

        result = await exponential_backoff(
            _wait_for_api_request,
            'Repeated api_request to proxy path "{}" failed.'.format(path),
            timeout=30,
        )
        return result

    async def add_route(self, routespec, target, data):
        body = data or {}
        body['target'] = target
        body['jupyterhub'] = True
        path = self._routespec_to_chp_path(routespec)
        await self.api_request(path, method='POST', body=body)

    async def delete_route(self, routespec):
        path = self._routespec_to_chp_path(routespec)
        try:
            await self.api_request(path, method='DELETE')
        except HTTPError as e:
            if e.code == 404:
                # Warn about 404s because something might be wrong
                # but don't raise because the route is gone,
                # which is the goal.
                self.log.warning("Route %s already deleted", routespec)
            else:
                raise

    def _reformat_routespec(self, routespec, chp_data):
        """Reformat CHP data format to JupyterHub's proxy API."""
        target = chp_data.pop('target')
        chp_data.pop('jupyterhub')
        return {'routespec': routespec, 'target': target, 'data': chp_data}

    async def get_all_routes(self, client=None):
        """Fetch the proxy's routes."""
        proxy_poll_start_time = time.perf_counter()
        resp = await self.api_request('', client=client)
        chp_routes = json.loads(resp.body.decode('utf8', 'replace'))
        all_routes = {}
        for chp_path, chp_data in chp_routes.items():
            routespec = self._routespec_from_chp_path(chp_path)
            if 'jupyterhub' not in chp_data:
                # exclude routes not associated with JupyterHub
                self.log.debug("Omitting non-jupyterhub route %r", routespec)
                continue
            all_routes[routespec] = self._reformat_routespec(routespec, chp_data)
        PROXY_POLL_DURATION_SECONDS.observe(time.perf_counter() - proxy_poll_start_time)
        return all_routes
