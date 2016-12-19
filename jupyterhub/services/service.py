"""A service is a process that talks to JupyterHub

Cases:

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
        'token': 'super-secret',
    }

A hub-managed service with no URL:

    {
        'name': 'cull-idle',
        'command': ['python', '/path/to/cull-idle']
        'admin': True,
    }
"""

from getpass import getuser
import pipes
import shutil
from subprocess import Popen
from urllib.parse import urlparse

from tornado import gen

from traitlets import (
    HasTraits,
    Any, Bool, Dict, Unicode, Instance,
    default, observe,
)
from traitlets.config import LoggingConfigurable

from .. import orm
from ..traitlets import Command
from ..spawner import LocalProcessSpawner
from ..utils import url_path_join

class _MockUser(HasTraits):
    name = Unicode()
    server = Instance(orm.Server, allow_none=True)
    state = Dict()
    service = Instance(__module__ + '.Service')

# We probably shouldn't use a Spawner here,
# but there are too many concepts to share.

class _ServiceSpawner(LocalProcessSpawner):
    """Subclass of LocalProcessSpawner

    Removes notebook-specific-ness from LocalProcessSpawner.
    """
    cwd = Unicode()
    cmd = Command(minlen=0)

    def make_preexec_fn(self, name):
        if not name or name == getuser():
            # no setuid if no name
            return
        return super().make_preexec_fn(name)

    def start(self):
        """Start the process"""
        env = self.get_env()
        cmd = self.cmd

        self.log.info("Spawning %s", ' '.join(pipes.quote(s) for s in cmd))
        try:
            self.proc = Popen(self.cmd, env=env,
                preexec_fn=self.make_preexec_fn(self.user.name),
                start_new_session=True, # don't forward signals
                cwd=self.cwd or None,
            )
        except PermissionError:
            # use which to get abspath
            script = shutil.which(cmd[0]) or cmd[0]
            self.log.error("Permission denied trying to run %r. Does %s have access to this file?",
                script, self.user.name,
            )
            raise

        self.pid = self.proc.pid

class Service(LoggingConfigurable):
    """An object wrapping a service specification for Hub API consumers.

    A service has inputs:

    - name: str
        the name of the service
    - admin: bool(false)
        whether the service should have administrative privileges
    - url: str (None)
        The URL where the service is/should be.
        If specified, the service will be added to the proxy at /services/:name

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
    admin = Bool(False,
        help="Does the service need admin-access to the Hub API?"
    ).tag(input=True)
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
    # Managed service API:

    @property
    def managed(self):
        """Am I managed by the Hub?"""
        return bool(self.command)

    command = Command(minlen=0,
        help="Command to spawn this service, if managed."
    ).tag(input=True)
    cwd = Unicode(
        help="""The working directory in which to run the service."""
    ).tag(input=True)
    environment = Dict(
        help="""Environment variables to pass to the service.
        Only used if the Hub is spawning the service.
        """
    ).tag(input=True)
    user = Unicode(getuser(),
        help="""The user to become when launching the service.

        If unspecified, run the service as the same user as the Hub.
        """
    ).tag(input=True)

    domain = Unicode()
    host = Unicode()
    proc = Any()

    # handles on globals:
    proxy = Any()
    base_url = Unicode()
    db = Any()
    orm = Any()

    @property
    def server(self):
        return self.orm.server

    @property
    def prefix(self):
        return url_path_join(self.base_url, 'services', self.name)

    @property
    def proxy_path(self):
        if not self.server:
            return ''
        if self.domain:
            return url_path_join('/' + self.domain, self.server.base_url)
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
        env['JUPYTERHUB_API_TOKEN'] = self.api_token
        env['JUPYTERHUB_API_URL'] = self.hub_api_url
        env['JUPYTERHUB_BASE_URL'] = self.base_url
        if self.url:
            env['JUPYTERHUB_SERVICE_URL'] = self.url
            env['JUPYTERHUB_SERVICE_PREFIX'] = self.server.base_url

        self.spawner = _ServiceSpawner(
            cmd=self.command,
            environment=env,
            api_token=self.api_token,
            cwd=self.cwd,
            user=_MockUser(
                name=self.user,
                service=self,
                server=self.orm.server,
            ),
        )
        self.spawner.start()
        self.proc = self.spawner.proc
        self.spawner.add_poll_callback(self._proc_stopped)
        self.spawner.start_polling()

    def _proc_stopped(self):
        """Called when the service process unexpectedly exits"""
        self.log.error("Service %s exited with status %i", self.name, self.proc.returncode)
        self.start()

    def stop(self):
        """Stop a managed service"""
        if not self.managed:
            raise RuntimeError("Cannot start unmanaged service %s" % self)
        self.spawner.stop_polling()
        return self.spawner.stop()
