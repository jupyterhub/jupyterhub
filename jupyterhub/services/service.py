"""A service is a process that talks to JupyterHub.

Types of services:
    Managed:
      - managed by JupyterHub (always subprocess, no custom Spawners)
      - always a long-running process
      - managed services are restarted automatically if they exit unexpectedly

    Unmanaged:
      - managed by external service (docker, systemd, etc.)
      - do not need to be long-running processes, or processes at all

URL: needs a route added to the proxy.
  - Public route will always be /services/service-name
  - url specified in config
  - if port is 0, Hub will select a port

API access:
  - admin: tokens will have admin-access to the API
  - not admin: tokens will only have non-admin access
    (not much they can do other than defer to Hub for auth)

An externally managed service running on a URL::

    {
        'name': 'my-service',
        'url': 'https://host:8888',
        'admin': True,
        'api_token': 'super-secret',
    }

A hub-managed service with no URL::

    {
        'name': 'cull-idle',
        'command': ['python', '/path/to/cull-idle']
        'admin': True,
    }

"""
import copy
import os
import pipes
import shutil
from subprocess import Popen

from traitlets import Any
from traitlets import Bool
from traitlets import default
from traitlets import Dict
from traitlets import HasTraits
from traitlets import Instance
from traitlets import Unicode
from traitlets.config import LoggingConfigurable

from .. import orm
from ..objects import Server
from ..spawner import LocalProcessSpawner
from ..spawner import set_user_setuid
from ..traitlets import Command
from ..utils import url_path_join


class _MockUser(HasTraits):
    name = Unicode()
    server = Instance(orm.Server, allow_none=True)
    state = Dict()
    service = Instance(__name__ + '.Service')
    host = Unicode()

    @property
    def url(self):
        if not self.server:
            return ''
        if self.host:
            return self.host + self.server.base_url
        else:
            return self.server.base_url

    @property
    def base_url(self):
        if not self.server:
            return ''
        return self.server.base_url


# We probably shouldn't use a Spawner here,
# but there are too many concepts to share.


class _ServiceSpawner(LocalProcessSpawner):
    """Subclass of LocalProcessSpawner

    Removes notebook-specific-ness from LocalProcessSpawner.
    """

    cwd = Unicode()
    cmd = Command(minlen=0)

    def make_preexec_fn(self, name):
        if not name:
            # no setuid if no name
            return
        return set_user_setuid(name, chdir=False)

    def user_env(self, env):
        if not self.user.name:
            return env
        else:
            return super().user_env(env)

    def start(self):
        """Start the process"""
        env = self.get_env()
        # no activity url for services
        env.pop('JUPYTERHUB_ACTIVITY_URL', None)
        if os.name == 'nt':
            env['SYSTEMROOT'] = os.environ['SYSTEMROOT']
        cmd = self.cmd

        self.log.info("Spawning %s", ' '.join(pipes.quote(s) for s in cmd))
        try:
            self.proc = Popen(
                self.cmd,
                env=env,
                preexec_fn=self.make_preexec_fn(self.user.name),
                start_new_session=True,  # don't forward signals
                cwd=self.cwd or None,
            )
        except PermissionError:
            # use which to get abspath
            script = shutil.which(cmd[0]) or cmd[0]
            self.log.error(
                "Permission denied trying to run %r. Does %s have access to this file?",
                script,
                self.user.name,
            )
            raise

        self.pid = self.proc.pid


class Service(LoggingConfigurable):
    """An object wrapping a service specification for Hub API consumers.

    A service has inputs:

    - name: str
        the name of the service
    - admin: bool(False)
        whether the service should have administrative privileges
    - url: str (None)
        The URL where the service is/should be.
        If specified, the service will be added to the proxy at /services/:name
    - oauth_no_confirm: bool(False)
        Whether this service should be allowed to complete oauth
        with logged-in users without prompting for confirmation.

    If a service is to be managed by the Hub, it has a few extra options:

    - command: (str/Popen list)
        Command for JupyterHub to spawn the service.
        Only use this if the service should be a subprocess.
        If command is not specified, it is assumed to be managed
        by a
    - environment: dict
        Additional environment variables for the service.
    - user: str
        The name of a system user to become.
        If unspecified, run as the same user as the Hub.
    """

    # inputs:
    name = Unicode(
        help="""The name of the service.

        If the service has an http endpoint, it
        """
    ).tag(input=True)
    admin = Bool(False, help="Does the service need admin-access to the Hub API?").tag(
        input=True
    )
    url = Unicode(
        help="""URL of the service.

        Only specify if the service runs an HTTP(s) endpoint that.
        If managed, will be passed as JUPYTERHUB_SERVICE_URL env.
        """
    ).tag(input=True)

    api_token = Unicode(
        help="""The API token to use for the service.

        If unspecified, an API token will be generated for managed services.
        """
    ).tag(input=True)

    info = Dict(
        help="""Provide a place to include miscellaneous information about the service,
        provided through the configuration
        """
    ).tag(input=True)

    display = Bool(
        True, help="""Whether to list the service on the JupyterHub UI"""
    ).tag(input=True)

    oauth_no_confirm = Bool(
        False,
        help="""Skip OAuth confirmation when users access this service.

        By default, when users authenticate with a service using JupyterHub,
        they are prompted to confirm that they want to grant that service
        access to their credentials.
        Setting oauth_no_confirm=True skips the confirmation web page for this service.
        Skipping the confirmation page is useful for admin-managed services that are considered part of the Hub
        and shouldn't need extra prompts for login.

        .. versionadded: 1.1
        """,
    ).tag(input=True)

    # Managed service API:
    spawner = Any()

    @property
    def managed(self):
        """Am I managed by the Hub?"""
        return bool(self.command)

    @property
    def kind(self):
        """The name of the kind of service as a string

        - 'managed' for managed services
        - 'external' for external services
        """
        return 'managed' if self.managed else 'external'

    command = Command(minlen=0, help="Command to spawn this service, if managed.").tag(
        input=True
    )
    cwd = Unicode(help="""The working directory in which to run the service.""").tag(
        input=True
    )
    environment = Dict(
        help="""Environment variables to pass to the service.
        Only used if the Hub is spawning the service.
        """
    ).tag(input=True)
    user = Unicode(
        "",
        help="""The user to become when launching the service.

        If unspecified, run the service as the same user as the Hub.
        """,
    ).tag(input=True)

    domain = Unicode()
    host = Unicode()
    hub = Any()
    app = Any()
    proc = Any()

    # handles on globals:
    proxy = Any()
    base_url = Unicode()
    db = Any()
    orm = Any()
    cookie_options = Dict()

    oauth_provider = Any()

    oauth_client_id = Unicode(
        help="""OAuth client ID for this service.

        You shouldn't generally need to change this.
        Default: `service-<name>`
        """
    ).tag(input=True)

    @default('oauth_client_id')
    def _default_client_id(self):
        return 'service-%s' % self.name

    oauth_redirect_uri = Unicode(
        help="""OAuth redirect URI for this service.

        You shouldn't generally need to change this.
        Default: `/services/:name/oauth_callback`
        """
    ).tag(input=True)

    @default('oauth_redirect_uri')
    def _default_redirect_uri(self):
        if self.server is None:
            return ''
        return self.host + url_path_join(self.prefix, 'oauth_callback')

    @property
    def oauth_available(self):
        """Is OAuth available for this client?

        Returns True if a server is defined or oauth_redirect_uri is specified manually
        """
        return bool(self.server is not None or self.oauth_redirect_uri)

    @property
    def server(self):
        if self.orm.server:
            return Server.from_orm(self.orm.server)
        else:
            return None

    @property
    def prefix(self):
        return url_path_join(self.base_url, 'services', self.name + '/')

    @property
    def proxy_spec(self):
        if not self.server:
            return ''
        if self.domain:
            return self.domain + self.server.base_url
        else:
            return self.server.base_url

    def __repr__(self):
        return "<{cls}(name={name}{managed})>".format(
            cls=self.__class__.__name__,
            name=self.name,
            managed=' managed' if self.managed else '',
        )

    def start(self):
        """Start a managed service"""
        if not self.managed:
            raise RuntimeError("Cannot start unmanaged service %s" % self)
        self.log.info("Starting service %r: %r", self.name, self.command)
        env = {}
        env.update(self.environment)

        env['JUPYTERHUB_SERVICE_NAME'] = self.name
        if self.url:
            env['JUPYTERHUB_SERVICE_URL'] = self.url
            env['JUPYTERHUB_SERVICE_PREFIX'] = self.server.base_url

        hub = self.hub
        if self.hub.ip in ('', '0.0.0.0', '::'):
            # if the Hub is listening on all interfaces,
            # tell services to connect via localhost
            # since they are always local subprocesses
            hub = copy.deepcopy(self.hub)
            hub.connect_url = ''
            hub.connect_ip = '127.0.0.1'

        self.spawner = _ServiceSpawner(
            cmd=self.command,
            environment=env,
            api_token=self.api_token,
            oauth_client_id=self.oauth_client_id,
            cookie_options=self.cookie_options,
            cwd=self.cwd,
            hub=self.hub,
            user=_MockUser(
                name=self.user, service=self, server=self.orm.server, host=self.host
            ),
            internal_ssl=self.app.internal_ssl,
            internal_certs_location=self.app.internal_certs_location,
            internal_trust_bundles=self.app.internal_trust_bundles,
        )
        self.spawner.start()
        self.proc = self.spawner.proc
        self.spawner.add_poll_callback(self._proc_stopped)
        self.spawner.start_polling()

    def _proc_stopped(self):
        """Called when the service process unexpectedly exits"""
        self.log.error(
            "Service %s exited with status %i", self.name, self.proc.returncode
        )
        self.start()

    async def stop(self):
        """Stop a managed service"""
        self.log.debug("Stopping service %s", self.name)
        if not self.managed:
            raise RuntimeError("Cannot stop unmanaged service %s" % self)
        if self.spawner:
            if self.orm.server:
                self.db.delete(self.orm.server)
                self.db.commit()
            self.spawner.stop_polling()
            return await self.spawner.stop()
