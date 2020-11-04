"""
Contains base Spawner class & default implementation
"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import ast
import json
import os
import pipes
import shutil
import signal
import sys
import warnings
from subprocess import Popen
from tempfile import mkdtemp

if os.name == 'nt':
    import psutil
from async_generator import async_generator
from async_generator import yield_
from sqlalchemy import inspect
from tornado.ioloop import PeriodicCallback
from traitlets import Any
from traitlets import Bool
from traitlets import default
from traitlets import Dict
from traitlets import Float
from traitlets import Instance
from traitlets import Integer
from traitlets import List
from traitlets import observe
from traitlets import Unicode
from traitlets import Union
from traitlets import validate
from traitlets.config import LoggingConfigurable

from .objects import Server
from .traitlets import ByteSpecification
from .traitlets import Callable
from .traitlets import Command
from .utils import exponential_backoff
from .utils import iterate_until
from .utils import maybe_future
from .utils import random_port
from .utils import url_path_join

# FIXME: remove when we drop Python 3.5 support


def _quote_safe(s):
    """pass a string that is safe on the command-line

    traitlets may parse literals on the command-line, e.g. `--ip=123` will be the number 123 instead of the *string* 123.
    wrap valid literals in repr to ensure they are safe
    """

    try:
        val = ast.literal_eval(s)
    except Exception:
        # not valid, leave it alone
        return s
    else:
        # it's a valid literal, wrap it in repr (usually just quotes, but with proper escapes)
        # to avoid getting interpreted by traitlets
        return repr(s)


class Spawner(LoggingConfigurable):
    """Base class for spawning single-user notebook servers.

    Subclass this, and override the following methods:

    - load_state
    - get_state
    - start
    - stop
    - poll

    As JupyterHub supports multiple users, an instance of the Spawner subclass
    is created for each user. If there are 20 JupyterHub users, there will be 20
    instances of the subclass.
    """

    # private attributes for tracking status
    _spawn_pending = False
    _start_pending = False
    _stop_pending = False
    _proxy_pending = False
    _check_pending = False
    _waiting_for_response = False
    _jupyterhub_version = None
    _spawn_future = None

    @property
    def _log_name(self):
        """Return username:servername or username

        Used in logging for consistency with named servers.
        """
        if self.name:
            return '%s:%s' % (self.user.name, self.name)
        else:
            return self.user.name

    @property
    def _failed(self):
        """Did the last spawn fail?"""
        return (
            not self.active
            and self._spawn_future
            and self._spawn_future.done()
            and self._spawn_future.exception()
        )

    @property
    def pending(self):
        """Return the current pending event, if any

        Return False if nothing is pending.
        """
        if self._spawn_pending:
            return 'spawn'
        elif self._stop_pending:
            return 'stop'
        elif self._check_pending:
            return 'check'
        return None

    @property
    def ready(self):
        """Is this server ready to use?

        A server is not ready if an event is pending.
        """
        if self.pending:
            return False
        if self.server is None:
            return False
        return True

    @property
    def active(self):
        """Return True if the server is active.

        This includes fully running and ready or any pending start/stop event.
        """
        return bool(self.pending or self.ready)

    # options passed by constructor
    authenticator = Any()
    hub = Any()
    orm_spawner = Any()
    db = Any()
    cookie_options = Dict()

    @observe('orm_spawner')
    def _orm_spawner_changed(self, change):
        if change.new and change.new.server:
            self._server = Server(orm_server=change.new.server)
        else:
            self._server = None

    user = Any()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

        missing = []
        for attr in ('start', 'stop', 'poll'):
            if getattr(Spawner, attr) is getattr(cls, attr):
                missing.append(attr)

        if missing:
            raise NotImplementedError(
                "class `{}` needs to redefine the `start`,"
                "`stop` and `poll` methods. `{}` not redefined.".format(
                    cls.__name__, '`, `'.join(missing)
                )
            )

    proxy_spec = Unicode()

    @property
    def last_activity(self):
        return self.orm_spawner.last_activity

    @property
    def server(self):
        if hasattr(self, '_server'):
            return self._server
        if self.orm_spawner and self.orm_spawner.server:
            return Server(orm_server=self.orm_spawner.server)

    @server.setter
    def server(self, server):
        self._server = server
        if self.orm_spawner:
            if self.orm_spawner.server is not None:
                # delete the old value
                db = inspect(self.orm_spawner.server).session
                db.delete(self.orm_spawner.server)
            if server is None:
                self.orm_spawner.server = None
            else:
                self.orm_spawner.server = server.orm_server

    @property
    def name(self):
        if self.orm_spawner:
            return self.orm_spawner.name
        return ''

    internal_ssl = Bool(False)
    internal_trust_bundles = Dict()
    internal_certs_location = Unicode('')
    cert_paths = Dict()
    admin_access = Bool(False)
    api_token = Unicode()
    oauth_client_id = Unicode()
    handler = Any()

    will_resume = Bool(
        False,
        help="""Whether the Spawner will resume on next start


        Default is False where each launch of the Spawner will be a new instance.
        If True, an existing Spawner will resume instead of starting anew
        (e.g. resuming a Docker container),
        and API tokens in use when the Spawner stops will not be deleted.
        """,
    )

    ip = Unicode(
        '',
        help="""
        The IP address (or hostname) the single-user server should listen on.

        The JupyterHub proxy implementation should be able to send packets to this interface.
        """,
    ).tag(config=True)

    port = Integer(
        0,
        help="""
        The port for single-user servers to listen on.

        Defaults to `0`, which uses a randomly allocated port number each time.

        If set to a non-zero value, all Spawners will use the same port,
        which only makes sense if each server is on a different address,
        e.g. in containers.

        New in version 0.7.
        """,
    ).tag(config=True)

    consecutive_failure_limit = Integer(
        0,
        help="""
        Maximum number of consecutive failures to allow before
        shutting down JupyterHub.

        This helps JupyterHub recover from a certain class of problem preventing launch
        in contexts where the Hub is automatically restarted (e.g. systemd, docker, kubernetes).

        A limit of 0 means no limit and consecutive failures will not be tracked.
        """,
    ).tag(config=True)

    start_timeout = Integer(
        60,
        help="""
        Timeout (in seconds) before giving up on starting of single-user server.

        This is the timeout for start to return, not the timeout for the server to respond.
        Callers of spawner.start will assume that startup has failed if it takes longer than this.
        start should return when the server process is started and its location is known.
        """,
    ).tag(config=True)

    http_timeout = Integer(
        30,
        help="""
        Timeout (in seconds) before giving up on a spawned HTTP server

        Once a server has successfully been spawned, this is the amount of time
        we wait before assuming that the server is unable to accept
        connections.
        """,
    ).tag(config=True)

    poll_interval = Integer(
        30,
        help="""
        Interval (in seconds) on which to poll the spawner for single-user server's status.

        At every poll interval, each spawner's `.poll` method is called, which checks
        if the single-user server is still running. If it isn't running, then JupyterHub modifies
        its own state accordingly and removes appropriate routes from the configurable proxy.
        """,
    ).tag(config=True)

    _callbacks = List()
    _poll_callback = Any()

    debug = Bool(False, help="Enable debug-logging of the single-user server").tag(
        config=True
    )

    options_form = Union(
        [Unicode(), Callable()],
        help="""
        An HTML form for options a user can specify on launching their server.

        The surrounding `<form>` element and the submit button are already provided.

        For example:

        .. code:: html

            Set your key:
            <input name="key" val="default_key"></input>
            <br>
            Choose a letter:
            <select name="letter" multiple="true">
              <option value="A">The letter A</option>
              <option value="B">The letter B</option>
            </select>

        The data from this form submission will be passed on to your spawner in `self.user_options`

        Instead of a form snippet string, this could also be a callable that takes as one
        parameter the current spawner instance and returns a string. The callable will
        be called asynchronously if it returns a future, rather than a str. Note that
        the interface of the spawner class is not deemed stable across versions,
        so using this functionality might cause your JupyterHub upgrades to break.
    """,
    ).tag(config=True)

    async def get_options_form(self):
        """Get the options form

        Returns:
          Future (str): the content of the options form presented to the user
          prior to starting a Spawner.

        .. versionadded:: 0.9
        """
        if callable(self.options_form):
            options_form = await maybe_future(self.options_form(self))
        else:
            options_form = self.options_form

        return options_form

    def options_from_form(self, form_data):
        """Interpret HTTP form data

        Form data will always arrive as a dict of lists of strings.
        Override this function to understand single-values, numbers, etc.

        This should coerce form data into the structure expected by self.user_options,
        which must be a dict, and should be JSON-serializeable,
        though it can contain bytes in addition to standard JSON data types.

        This method should not have any side effects.
        Any handling of `user_options` should be done in `.start()`
        to ensure consistent behavior across servers
        spawned via the API and form submission page.

        Instances will receive this data on self.user_options, after passing through this function,
        prior to `Spawner.start`.

        .. versionchanged:: 1.0
            user_options are persisted in the JupyterHub database to be reused
            on subsequent spawns if no options are given.
            user_options is serialized to JSON as part of this persistence
            (with additional support for bytes in case of uploaded file data),
            and any non-bytes non-jsonable values will be replaced with None
            if the user_options are re-used.
        """
        return form_data

    def options_from_query(self, query_data):
        """Interpret query arguments passed to /spawn

        Query arguments will always arrive as a dict of unicode strings.
        Override this function to understand single-values, numbers, etc.

        By default, options_from_form is called from this function. You can however override
        this function if you need to process the query arguments differently.

        This should coerce form data into the structure expected by self.user_options,
        which must be a dict, and should be JSON-serializeable,
        though it can contain bytes in addition to standard JSON data types.

        This method should not have any side effects.
        Any handling of `user_options` should be done in `.start()`
        to ensure consistent behavior across servers
        spawned via the API and form submission page.

        Instances will receive this data on self.user_options, after passing through this function,
        prior to `Spawner.start`.

        .. versionadded:: 1.2
            user_options are persisted in the JupyterHub database to be reused
            on subsequent spawns if no options are given.
            user_options is serialized to JSON as part of this persistence
            (with additional support for bytes in case of uploaded file data),
            and any non-bytes non-jsonable values will be replaced with None
            if the user_options are re-used.
        """
        return self.options_from_form(query_data)

    user_options = Dict(
        help="""
        Dict of user specified options for the user's spawned instance of a single-user server.

        These user options are usually provided by the `options_form` displayed to the user when they start
        their server.
        """
    )

    env_keep = List(
        [
            'PATH',
            'PYTHONPATH',
            'CONDA_ROOT',
            'CONDA_DEFAULT_ENV',
            'VIRTUAL_ENV',
            'LANG',
            'LC_ALL',
            'JUPYTERHUB_SINGLEUSER_APP',
        ],
        help="""
        List of environment variables for the single-user server to inherit from the JupyterHub process.

        This list is used to ensure that sensitive information in the JupyterHub process's environment
        (such as `CONFIGPROXY_AUTH_TOKEN`) is not passed to the single-user server's process.
        """,
    ).tag(config=True)

    env = Dict(
        help="""Deprecated: use Spawner.get_env or Spawner.environment

    - extend Spawner.get_env for adding required env in Spawner subclasses
    - Spawner.environment for config-specified env
    """
    )

    environment = Dict(
        help="""
        Extra environment variables to set for the single-user server's process.

        Environment variables that end up in the single-user server's process come from 3 sources:
          - This `environment` configurable
          - The JupyterHub process' environment variables that are listed in `env_keep`
          - Variables to establish contact between the single-user notebook and the hub (such as JUPYTERHUB_API_TOKEN)

        The `environment` configurable should be set by JupyterHub administrators to add
        installation specific environment variables. It is a dict where the key is the name of the environment
        variable, and the value can be a string or a callable. If it is a callable, it will be called
        with one parameter (the spawner instance), and should return a string fairly quickly (no blocking
        operations please!).

        Note that the spawner class' interface is not guaranteed to be exactly same across upgrades,
        so if you are using the callable take care to verify it continues to work after upgrades!

        .. versionchanged:: 1.2
            environment from this configuration has highest priority,
            allowing override of 'default' env variables,
            such as JUPYTERHUB_API_URL.
        """
    ).tag(config=True)

    cmd = Command(
        ['jupyterhub-singleuser'],
        allow_none=True,
        help="""
        The command used for starting the single-user server.

        Provide either a string or a list containing the path to the startup script command. Extra arguments,
        other than this path, should be provided via `args`.

        This is usually set if you want to start the single-user server in a different python
        environment (with virtualenv/conda) than JupyterHub itself.

        Some spawners allow shell-style expansion here, allowing you to use environment variables.
        Most, including the default, do not. Consult the documentation for your spawner to verify!
        """,
    ).tag(config=True)

    args = List(
        Unicode(),
        help="""
        Extra arguments to be passed to the single-user server.

        Some spawners allow shell-style expansion here, allowing you to use environment variables here.
        Most, including the default, do not. Consult the documentation for your spawner to verify!
        """,
    ).tag(config=True)

    notebook_dir = Unicode(
        help="""
        Path to the notebook directory for the single-user server.

        The user sees a file listing of this directory when the notebook interface is started. The
        current interface does not easily allow browsing beyond the subdirectories in this directory's
        tree.

        `~` will be expanded to the home directory of the user, and {username} will be replaced
        with the name of the user.

        Note that this does *not* prevent users from accessing files outside of this path! They
        can do so with many other means.
        """
    ).tag(config=True)

    default_url = Unicode(
        help="""
        The URL the single-user server should start in.

        `{username}` will be expanded to the user's username

        Example uses:

        - You can set `notebook_dir` to `/` and `default_url` to `/tree/home/{username}` to allow people to
          navigate the whole filesystem from their notebook server, but still start in their home directory.
        - Start with `/notebooks` instead of `/tree` if `default_url` points to a notebook instead of a directory.
        - You can set this to `/lab` to have JupyterLab start by default, rather than Jupyter Notebook.
        """
    ).tag(config=True)

    @validate('notebook_dir', 'default_url')
    def _deprecate_percent_u(self, proposal):
        v = proposal['value']
        if '%U' in v:
            self.log.warning(
                "%%U for username in %s is deprecated in JupyterHub 0.7, use {username}",
                proposal['trait'].name,
            )
            v = v.replace('%U', '{username}')
            self.log.warning("Converting %r to %r", proposal['value'], v)
        return v

    disable_user_config = Bool(
        False,
        help="""
        Disable per-user configuration of single-user servers.

        When starting the user's single-user server, any config file found in the user's $HOME directory
        will be ignored.

        Note: a user could circumvent this if the user modifies their Python environment, such as when
        they have their own conda environments / virtualenvs / containers.
        """,
    ).tag(config=True)

    mem_limit = ByteSpecification(
        None,
        help="""
        Maximum number of bytes a single-user notebook server is allowed to use.

        Allows the following suffixes:
          - K -> Kilobytes
          - M -> Megabytes
          - G -> Gigabytes
          - T -> Terabytes

        If the single user server tries to allocate more memory than this,
        it will fail. There is no guarantee that the single-user notebook server
        will be able to allocate this much memory - only that it can not
        allocate more than this.

        **This is a configuration setting. Your spawner must implement support
        for the limit to work.** The default spawner, `LocalProcessSpawner`,
        does **not** implement this support. A custom spawner **must** add
        support for this setting for it to be enforced.
        """,
    ).tag(config=True)

    cpu_limit = Float(
        None,
        allow_none=True,
        help="""
        Maximum number of cpu-cores a single-user notebook server is allowed to use.

        If this value is set to 0.5, allows use of 50% of one CPU.
        If this value is set to 2, allows use of up to 2 CPUs.

        The single-user notebook server will never be scheduled by the kernel to
        use more cpu-cores than this. There is no guarantee that it can
        access this many cpu-cores.

        **This is a configuration setting. Your spawner must implement support
        for the limit to work.** The default spawner, `LocalProcessSpawner`,
        does **not** implement this support. A custom spawner **must** add
        support for this setting for it to be enforced.
        """,
    ).tag(config=True)

    mem_guarantee = ByteSpecification(
        None,
        help="""
        Minimum number of bytes a single-user notebook server is guaranteed to have available.

        Allows the following suffixes:
          - K -> Kilobytes
          - M -> Megabytes
          - G -> Gigabytes
          - T -> Terabytes

        **This is a configuration setting. Your spawner must implement support
        for the limit to work.** The default spawner, `LocalProcessSpawner`,
        does **not** implement this support. A custom spawner **must** add
        support for this setting for it to be enforced.
        """,
    ).tag(config=True)

    cpu_guarantee = Float(
        None,
        allow_none=True,
        help="""
        Minimum number of cpu-cores a single-user notebook server is guaranteed to have available.

        If this value is set to 0.5, allows use of 50% of one CPU.
        If this value is set to 2, allows use of up to 2 CPUs.

        **This is a configuration setting. Your spawner must implement support
        for the limit to work.** The default spawner, `LocalProcessSpawner`,
        does **not** implement this support. A custom spawner **must** add
        support for this setting for it to be enforced.
        """,
    ).tag(config=True)

    pre_spawn_hook = Any(
        help="""
        An optional hook function that you can implement to do some
        bootstrapping work before the spawner starts. For example, create a
        directory for your user or load initial content.

        This can be set independent of any concrete spawner implementation.

        This maybe a coroutine.

        Example::

            from subprocess import check_call
            def my_hook(spawner):
                username = spawner.user.name
                check_call(['./examples/bootstrap-script/bootstrap.sh', username])

            c.Spawner.pre_spawn_hook = my_hook

        """
    ).tag(config=True)

    post_stop_hook = Any(
        help="""
        An optional hook function that you can implement to do work after
        the spawner stops.

        This can be set independent of any concrete spawner implementation.
        """
    ).tag(config=True)

    auth_state_hook = Any(
        help="""
        An optional hook function that you can implement to pass `auth_state`
        to the spawner after it has been initialized but before it starts.
        The `auth_state` dictionary may be set by the `.authenticate()`
        method of the authenticator.  This hook enables you to pass some
        or all of that information to your spawner.

        Example::

            def userdata_hook(spawner, auth_state):
                spawner.userdata = auth_state["userdata"]

            c.Spawner.auth_state_hook = userdata_hook

        """
    ).tag(config=True)

    def load_state(self, state):
        """Restore state of spawner from database.

        Called for each user's spawner after the hub process restarts.

        `state` is a dict that'll contain the value returned by `get_state` of
        the spawner, or {} if the spawner hasn't persisted any state yet.

        Override in subclasses to restore any extra state that is needed to track
        the single-user server for that user. Subclasses should call super().
        """
        pass

    def get_state(self):
        """Save state of spawner into database.

        A black box of extra state for custom spawners. The returned value of this is
        passed to `load_state`.

        Subclasses should call `super().get_state()`, augment the state returned from
        there, and return that state.

        Returns
        -------
        state: dict
             a JSONable dict of state
        """
        state = {}
        return state

    def clear_state(self):
        """Clear any state that should be cleared when the single-user server stops.

        State that should be preserved across single-user server instances should not be cleared.

        Subclasses should call super, to ensure that state is properly cleared.
        """
        self.api_token = ''

    def get_env(self):
        """Return the environment dict to use for the Spawner.

        This applies things like `env_keep`, anything defined in `Spawner.environment`,
        and adds the API token to the env.

        When overriding in subclasses, subclasses must call `super().get_env()`, extend the
        returned dict and return it.

        Use this to access the env in Spawner.start to allow extension in subclasses.
        """
        env = {}
        if self.env:
            warnings.warn(
                "Spawner.env is deprecated, found %s" % self.env, DeprecationWarning
            )
            env.update(self.env)

        for key in self.env_keep:
            if key in os.environ:
                env[key] = os.environ[key]

        env['JUPYTERHUB_API_TOKEN'] = self.api_token
        # deprecated (as of 0.7.2), for old versions of singleuser
        env['JPY_API_TOKEN'] = self.api_token
        if self.admin_access:
            env['JUPYTERHUB_ADMIN_ACCESS'] = '1'
        # OAuth settings
        env['JUPYTERHUB_CLIENT_ID'] = self.oauth_client_id
        if self.cookie_options:
            env['JUPYTERHUB_COOKIE_OPTIONS'] = json.dumps(self.cookie_options)
        env['JUPYTERHUB_HOST'] = self.hub.public_host
        env['JUPYTERHUB_OAUTH_CALLBACK_URL'] = url_path_join(
            self.user.url, self.name, 'oauth_callback'
        )

        # Info previously passed on args
        env['JUPYTERHUB_USER'] = self.user.name
        env['JUPYTERHUB_SERVER_NAME'] = self.name
        env['JUPYTERHUB_API_URL'] = self.hub.api_url
        env['JUPYTERHUB_ACTIVITY_URL'] = url_path_join(
            self.hub.api_url,
            'users',
            # tolerate mocks defining only user.name
            getattr(self.user, 'escaped_name', self.user.name),
            'activity',
        )
        env['JUPYTERHUB_BASE_URL'] = self.hub.base_url[:-4]
        if self.server:
            env['JUPYTERHUB_SERVICE_PREFIX'] = self.server.base_url

        # Put in limit and guarantee info if they exist.
        # Note that this is for use by the humans / notebook extensions in the
        # single-user notebook server, and not for direct usage by the spawners
        # themselves. Spawners should just use the traitlets directly.
        if self.mem_limit:
            env['MEM_LIMIT'] = str(self.mem_limit)
        if self.mem_guarantee:
            env['MEM_GUARANTEE'] = str(self.mem_guarantee)
        if self.cpu_limit:
            env['CPU_LIMIT'] = str(self.cpu_limit)
        if self.cpu_guarantee:
            env['CPU_GUARANTEE'] = str(self.cpu_guarantee)

        if self.cert_paths:
            env['JUPYTERHUB_SSL_KEYFILE'] = self.cert_paths['keyfile']
            env['JUPYTERHUB_SSL_CERTFILE'] = self.cert_paths['certfile']
            env['JUPYTERHUB_SSL_CLIENT_CA'] = self.cert_paths['cafile']

        # env overrides from config. If the value is a callable, it will be called with
        # one parameter - the current spawner instance - and the return value
        # will be assigned to the environment variable. This will be called at
        # spawn time.
        # Called last to ensure highest priority, in case of overriding other
        # 'default' variables like the API url
        for key, value in self.environment.items():
            if callable(value):
                env[key] = value(self)
            else:
                env[key] = value

        return env

    async def get_url(self):
        """Get the URL to connect to the server

        Sometimes JupyterHub may ask the Spawner for its url.
        This can occur e.g. when JupyterHub has restarted while a server was not finished starting,
        giving Spawners a chance to recover the URL where their server is running.

        The default is to trust that JupyterHub has the right information.
        Only override this method in Spawners that know how to
        check the correct URL for the servers they start.

        This will only be asked of Spawners that claim to be running
        (`poll()` returns `None`).
        """
        return self.server.url

    def template_namespace(self):
        """Return the template namespace for format-string formatting.

        Currently used on default_url and notebook_dir.

        Subclasses may add items to the available namespace.

        The default implementation includes::

            {
              'username': user.name,
              'base_url': users_base_url,
            }

        Returns:

            ns (dict): namespace for string formatting.
        """
        d = {'username': self.user.name}
        if self.server:
            d['base_url'] = self.server.base_url
        return d

    def format_string(self, s):
        """Render a Python format string

        Uses :meth:`Spawner.template_namespace` to populate format namespace.

        Args:

            s (str): Python format-string to be formatted.

        Returns:

            str: Formatted string, rendered
        """
        return s.format(**self.template_namespace())

    trusted_alt_names = List(Unicode())

    ssl_alt_names = List(
        Unicode(),
        config=True,
        help="""List of SSL alt names

        May be set in config if all spawners should have the same value(s),
        or set at runtime by Spawner that know their names.
        """,
    )

    @default('ssl_alt_names')
    def _default_ssl_alt_names(self):
        # by default, use trusted_alt_names
        # inherited from global app
        return list(self.trusted_alt_names)

    ssl_alt_names_include_local = Bool(
        True,
        config=True,
        help="""Whether to include DNS:localhost, IP:127.0.0.1 in alt names""",
    )

    async def create_certs(self):
        """Create and set ownership for the certs to be used for internal ssl

        Keyword Arguments:
            alt_names (list): a list of alternative names to identify the
            server by, see:
            https://en.wikipedia.org/wiki/Subject_Alternative_Name

            override: override the default_names with the provided alt_names

        Returns:
            dict: Path to cert files and CA

        This method creates certs for use with the singleuser notebook. It
        enables SSL and ensures that the notebook can perform bi-directional
        SSL auth with the hub (verification based on CA).

        If the singleuser host has a name or ip other than localhost,
        an appropriate alternative name(s) must be passed for ssl verification
        by the hub to work. For example, for Jupyter hosts with an IP of
        10.10.10.10 or DNS name of jupyter.example.com, this would be:

        alt_names=["IP:10.10.10.10"]
        alt_names=["DNS:jupyter.example.com"]

        respectively. The list can contain both the IP and DNS names to refer
        to the host by either IP or DNS name (note the `default_names` below).
        """
        from certipy import Certipy

        default_names = ["DNS:localhost", "IP:127.0.0.1"]
        alt_names = []
        alt_names.extend(self.ssl_alt_names)

        if self.ssl_alt_names_include_local:
            alt_names = default_names + alt_names

        self.log.info("Creating certs for %s: %s", self._log_name, ';'.join(alt_names))

        common_name = self.user.name or 'service'
        certipy = Certipy(store_dir=self.internal_certs_location)
        notebook_component = 'notebooks-ca'
        notebook_key_pair = certipy.create_signed_pair(
            'user-' + common_name,
            notebook_component,
            alt_names=alt_names,
            overwrite=True,
        )
        paths = {
            "keyfile": notebook_key_pair['files']['key'],
            "certfile": notebook_key_pair['files']['cert'],
            "cafile": self.internal_trust_bundles[notebook_component],
        }
        return paths

    async def move_certs(self, paths):
        """Takes certificate paths and makes them available to the notebook server

        Arguments:
            paths (dict): a list of paths for key, cert, and CA.
                These paths will be resolvable and readable by the Hub process,
                but not necessarily by the notebook server.

        Returns:
            dict: a list (potentially altered) of paths for key, cert, and CA.
                These paths should be resolvable and readable by the notebook
                server to be launched.


        `.move_certs` is called after certs for the singleuser notebook have
        been created by create_certs.

        By default, certs are created in a standard, central location defined
        by `internal_certs_location`. For a local, single-host deployment of
        JupyterHub, this should suffice. If, however, singleuser notebooks
        are spawned on other hosts, `.move_certs` should be overridden to move
        these files appropriately. This could mean using `scp` to copy them
        to another host, moving them to a volume mounted in a docker container,
        or exporting them as a secret in kubernetes.
        """
        return paths

    def get_args(self):
        """Return the arguments to be passed after self.cmd

        Doesn't expect shell expansion to happen.
        """
        args = []

        if self.ip:
            args.append('--ip=%s' % _quote_safe(self.ip))

        if self.port:
            args.append('--port=%i' % self.port)
        elif self.server and self.server.port:
            self.log.warning(
                "Setting port from user.server is deprecated as of JupyterHub 0.7."
            )
            args.append('--port=%i' % self.server.port)

        if self.notebook_dir:
            notebook_dir = self.format_string(self.notebook_dir)
            args.append('--notebook-dir=%s' % _quote_safe(notebook_dir))
        if self.default_url:
            default_url = self.format_string(self.default_url)
            args.append(
                '--SingleUserNotebookApp.default_url=%s' % _quote_safe(default_url)
            )

        if self.debug:
            args.append('--debug')
        if self.disable_user_config:
            args.append('--disable-user-config')
        args.extend(self.args)
        return args

    def run_pre_spawn_hook(self):
        """Run the pre_spawn_hook if defined"""
        if self.pre_spawn_hook:
            return self.pre_spawn_hook(self)

    def run_post_stop_hook(self):
        """Run the post_stop_hook if defined"""
        if self.post_stop_hook is not None:
            try:
                return self.post_stop_hook(self)
            except Exception:
                self.log.exception("post_stop_hook failed with exception: %s", self)

    async def run_auth_state_hook(self, auth_state):
        """Run the auth_state_hook if defined"""
        if self.auth_state_hook is not None:
            try:
                await maybe_future(self.auth_state_hook(self, auth_state))
            except Exception:
                self.log.exception("auth_stop_hook failed with exception: %s", self)

    @property
    def _progress_url(self):
        return self.user.progress_url(self.name)

    @async_generator
    async def _generate_progress(self):
        """Private wrapper of progress generator

        This method is always an async generator and will always yield at least one event.
        """
        if not self._spawn_pending:
            self.log.warning(
                "Spawn not pending, can't generate progress for %s", self._log_name
            )
            return

        await yield_({"progress": 0, "message": "Server requested"})
        from async_generator import aclosing

        async with aclosing(self.progress()) as progress:
            async for event in progress:
                await yield_(event)

    @async_generator
    async def progress(self):
        """Async generator for progress events

        Must be an async generator

        For Python 3.5-compatibility, use the async_generator package

        Should yield messages of the form:

        ::

          {
            "progress": 80, # integer, out of 100
            "message": text, # text message (will be escaped for HTML)
            "html_message": html_text, # optional html-formatted message (may have links)
          }

        In HTML contexts, html_message will be displayed instead of message if present.
        Progress will be updated if defined.
        To update messages without progress omit the progress field.

        .. versionadded:: 0.9
        """
        await yield_({"progress": 50, "message": "Spawning server..."})

    async def start(self):
        """Start the single-user server

        Returns:
          (str, int): the (ip, port) where the Hub can connect to the server.

        .. versionchanged:: 0.7
            Return ip, port instead of setting on self.user.server directly.
        """
        raise NotImplementedError(
            "Override in subclass. Must be a Tornado gen.coroutine."
        )

    async def stop(self, now=False):
        """Stop the single-user server

        If `now` is False (default), shutdown the server as gracefully as possible,
        e.g. starting with SIGINT, then SIGTERM, then SIGKILL.
        If `now` is True, terminate the server immediately.

        The coroutine should return when the single-user server process is no longer running.

        Must be a coroutine.
        """
        raise NotImplementedError(
            "Override in subclass. Must be a Tornado gen.coroutine."
        )

    async def poll(self):
        """Check if the single-user process is running

        Returns:
          None if single-user process is running.
          Integer exit status (0 if unknown), if it is not running.

        State transitions, behavior, and return response:

        - If the Spawner has not been initialized (neither loaded state, nor called start),
          it should behave as if it is not running (status=0).
        - If the Spawner has not finished starting,
          it should behave as if it is running (status=None).

        Design assumptions about when `poll` may be called:

        - On Hub launch: `poll` may be called before `start` when state is loaded on Hub launch.
          `poll` should return exit status 0 (unknown) if the Spawner has not been initialized via
          `load_state` or `start`.
        - If `.start()` is async: `poll` may be called during any yielded portions of the `start`
          process. `poll` should return None when `start` is yielded, indicating that the `start`
          process has not yet completed.

        """
        raise NotImplementedError(
            "Override in subclass. Must be a Tornado gen.coroutine."
        )

    def add_poll_callback(self, callback, *args, **kwargs):
        """Add a callback to fire when the single-user server stops"""
        if args or kwargs:
            cb = callback
            callback = lambda: cb(*args, **kwargs)
        self._callbacks.append(callback)

    def stop_polling(self):
        """Stop polling for single-user server's running state"""
        if self._poll_callback:
            self._poll_callback.stop()
            self._poll_callback = None

    def start_polling(self):
        """Start polling periodically for single-user server's running state.

        Callbacks registered via `add_poll_callback` will fire if/when the server stops.
        Explicit termination via the stop method will not trigger the callbacks.
        """
        if self.poll_interval <= 0:
            self.log.debug("Not polling subprocess")
            return
        else:
            self.log.debug("Polling subprocess every %is", self.poll_interval)

        self.stop_polling()

        self._poll_callback = PeriodicCallback(
            self.poll_and_notify, 1e3 * self.poll_interval
        )
        self._poll_callback.start()

    async def poll_and_notify(self):
        """Used as a callback to periodically poll the process and notify any watchers"""
        status = await self.poll()
        if status is None:
            # still running, nothing to do here
            return

        self.stop_polling()

        # clear callbacks list
        self._callbacks, callbacks = ([], self._callbacks)

        for callback in callbacks:
            try:
                await maybe_future(callback())
            except Exception:
                self.log.exception("Unhandled error in poll callback for %s", self)
        return status

    death_interval = Float(0.1)

    async def wait_for_death(self, timeout=10):
        """Wait for the single-user server to die, up to timeout seconds"""

        async def _wait_for_death():
            status = await self.poll()
            return status is not None

        try:
            r = await exponential_backoff(
                _wait_for_death,
                'Process did not die in {timeout} seconds'.format(timeout=timeout),
                start_wait=self.death_interval,
                timeout=timeout,
            )
            return r
        except TimeoutError:
            return False


def _try_setcwd(path):
    """Try to set CWD to path, walking up until a valid directory is found.

    If no valid directory is found, a temp directory is created and cwd is set to that.
    """
    while path != '/':
        try:
            os.chdir(path)
        except OSError as e:
            exc = e  # break exception instance out of except scope
            print("Couldn't set CWD to %s (%s)" % (path, e), file=sys.stderr)
            path, _ = os.path.split(path)
        else:
            return
    print("Couldn't set CWD at all (%s), using temp dir" % exc, file=sys.stderr)
    td = mkdtemp()
    os.chdir(td)


def set_user_setuid(username, chdir=True):
    """Return a preexec_fn for spawning a single-user server as a particular user.

    Returned preexec_fn will set uid/gid, and attempt to chdir to the target user's
    home directory.
    """
    import grp
    import pwd

    user = pwd.getpwnam(username)
    uid = user.pw_uid
    gid = user.pw_gid
    home = user.pw_dir
    gids = [g.gr_gid for g in grp.getgrall() if username in g.gr_mem]

    def preexec():
        """Set uid/gid of current process

        Executed after fork but before exec by python.

        Also try to chdir to the user's home directory.
        """
        os.setgid(gid)
        try:
            os.setgroups(gids)
        except Exception as e:
            print('Failed to set groups %s' % e, file=sys.stderr)
        os.setuid(uid)

        # start in the user's home dir
        if chdir:
            _try_setcwd(home)

    return preexec


class LocalProcessSpawner(Spawner):
    """
    A Spawner that uses `subprocess.Popen` to start single-user servers as local processes.

    Requires local UNIX users matching the authenticated users to exist.
    Does not work on Windows.

    This is the default spawner for JupyterHub.

    Note: This spawner does not implement CPU / memory guarantees and limits.
    """

    interrupt_timeout = Integer(
        10,
        help="""
        Seconds to wait for single-user server process to halt after SIGINT.

        If the process has not exited cleanly after this many seconds, a SIGTERM is sent.
        """,
    ).tag(config=True)

    term_timeout = Integer(
        5,
        help="""
        Seconds to wait for single-user server process to halt after SIGTERM.

        If the process does not exit cleanly after this many seconds of SIGTERM, a SIGKILL is sent.
        """,
    ).tag(config=True)

    kill_timeout = Integer(
        5,
        help="""
        Seconds to wait for process to halt after SIGKILL before giving up.

        If the process does not exit cleanly after this many seconds of SIGKILL, it becomes a zombie
        process. The hub process will log a warning and then give up.
        """,
    ).tag(config=True)

    popen_kwargs = Dict(
        help="""Extra keyword arguments to pass to Popen

        when spawning single-user servers.

        For example::

            popen_kwargs = dict(shell=True)

        """
    ).tag(config=True)
    shell_cmd = Command(
        minlen=0,
        help="""Specify a shell command to launch.

        The single-user command will be appended to this list,
        so it sould end with `-c` (for bash) or equivalent.

        For example::

            c.LocalProcessSpawner.shell_cmd = ['bash', '-l', '-c']

        to launch with a bash login shell, which would set up the user's own complete environment.

        .. warning::

            Using shell_cmd gives users control over PATH, etc.,
            which could change what the jupyterhub-singleuser launch command does.
            Only use this for trusted users.
        """,
    ).tag(config=True)

    proc = Instance(
        Popen,
        allow_none=True,
        help="""
        The process representing the single-user server process spawned for current user.

        Is None if no process has been spawned yet.
        """,
    )
    pid = Integer(
        0,
        help="""
        The process id (pid) of the single-user server process spawned for current user.
        """,
    )

    def make_preexec_fn(self, name):
        """
        Return a function that can be used to set the user id of the spawned process to user with name `name`

        This function can be safely passed to `preexec_fn` of `Popen`
        """
        return set_user_setuid(name)

    def load_state(self, state):
        """Restore state about spawned single-user server after a hub restart.

        Local processes only need the process id.
        """
        super(LocalProcessSpawner, self).load_state(state)
        if 'pid' in state:
            self.pid = state['pid']

    def get_state(self):
        """Save state that is needed to restore this spawner instance after a hub restore.

        Local processes only need the process id.
        """
        state = super(LocalProcessSpawner, self).get_state()
        if self.pid:
            state['pid'] = self.pid
        return state

    def clear_state(self):
        """Clear stored state about this spawner (pid)"""
        super(LocalProcessSpawner, self).clear_state()
        self.pid = 0

    def user_env(self, env):
        """Augment environment of spawned process with user specific env variables."""
        import pwd

        env['USER'] = self.user.name
        home = pwd.getpwnam(self.user.name).pw_dir
        shell = pwd.getpwnam(self.user.name).pw_shell
        # These will be empty if undefined,
        # in which case don't set the env:
        if home:
            env['HOME'] = home
        if shell:
            env['SHELL'] = shell
        return env

    def get_env(self):
        """Get the complete set of environment variables to be set in the spawned process."""
        env = super().get_env()
        env = self.user_env(env)
        return env

    async def move_certs(self, paths):
        """Takes cert paths, moves and sets ownership for them

        Arguments:
            paths (dict): a list of paths for key, cert, and CA

        Returns:
            dict: a list (potentially altered) of paths for key, cert,
            and CA

        Stage certificates into a private home directory
        and make them readable by the user.
        """
        import pwd

        key = paths['keyfile']
        cert = paths['certfile']
        ca = paths['cafile']

        user = pwd.getpwnam(self.user.name)
        uid = user.pw_uid
        gid = user.pw_gid
        home = user.pw_dir

        # Create dir for user's certs wherever we're starting
        hub_dir = "{home}/.jupyterhub".format(home=home)
        out_dir = "{hub_dir}/jupyterhub-certs".format(hub_dir=hub_dir)
        shutil.rmtree(out_dir, ignore_errors=True)
        os.makedirs(out_dir, 0o700, exist_ok=True)

        # Move certs to users dir
        shutil.move(paths['keyfile'], out_dir)
        shutil.move(paths['certfile'], out_dir)
        shutil.copy(paths['cafile'], out_dir)

        key = os.path.join(out_dir, os.path.basename(paths['keyfile']))
        cert = os.path.join(out_dir, os.path.basename(paths['certfile']))
        ca = os.path.join(out_dir, os.path.basename(paths['cafile']))

        # Set cert ownership to user
        for f in [hub_dir, out_dir, key, cert, ca]:
            shutil.chown(f, user=uid, group=gid)

        return {"keyfile": key, "certfile": cert, "cafile": ca}

    async def start(self):
        """Start the single-user server."""
        self.port = random_port()
        cmd = []
        env = self.get_env()

        cmd.extend(self.cmd)
        cmd.extend(self.get_args())

        if self.shell_cmd:
            # using shell_cmd (e.g. bash -c),
            # add our cmd list as the last (single) argument:
            cmd = self.shell_cmd + [' '.join(pipes.quote(s) for s in cmd)]

        self.log.info("Spawning %s", ' '.join(pipes.quote(s) for s in cmd))

        popen_kwargs = dict(
            preexec_fn=self.make_preexec_fn(self.user.name),
            start_new_session=True,  # don't forward signals
        )
        popen_kwargs.update(self.popen_kwargs)
        # don't let user config override env
        popen_kwargs['env'] = env
        try:
            self.proc = Popen(cmd, **popen_kwargs)
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

        if self.__class__ is not LocalProcessSpawner:
            # subclasses may not pass through return value of super().start,
            # relying on deprecated 0.6 way of setting ip, port,
            # so keep a redundant copy here for now.
            # A deprecation warning will be shown if the subclass
            # does not return ip, port.
            if self.ip:
                self.server.ip = self.ip
            self.server.port = self.port
            self.db.commit()
        return (self.ip or '127.0.0.1', self.port)

    async def poll(self):
        """Poll the spawned process to see if it is still running.

        If the process is still running, we return None. If it is not running,
        we return the exit code of the process if we have access to it, or 0 otherwise.
        """
        # if we started the process, poll with Popen
        if self.proc is not None:
            status = self.proc.poll()
            if status is not None:
                # clear state if the process is done
                self.clear_state()
            return status

        # if we resumed from stored state,
        # we don't have the Popen handle anymore, so rely on self.pid
        if not self.pid:
            # no pid, not running
            self.clear_state()
            return 0

        # We use pustil.pid_exists on windows
        if os.name == 'nt':
            alive = psutil.pid_exists(self.pid)
        else:
            alive = await self._signal(0)
        if not alive:
            self.clear_state()
            return 0
        else:
            return None

    async def _signal(self, sig):
        """Send given signal to a single-user server's process.

        Returns True if the process still exists, False otherwise.

        The hub process is assumed to have enough privileges to do this (e.g. root).
        """
        try:
            os.kill(self.pid, sig)
        except ProcessLookupError:
            return False  # process is gone
        except OSError as e:
            raise  # Can be EPERM or EINVAL
        return True  # process exists

    async def stop(self, now=False):
        """Stop the single-user server process for the current user.

        If `now` is False (default), shutdown the server as gracefully as possible,
        e.g. starting with SIGINT, then SIGTERM, then SIGKILL.
        If `now` is True, terminate the server immediately.

        The coroutine should return when the process is no longer running.
        """
        if not now:
            status = await self.poll()
            if status is not None:
                return
            self.log.debug("Interrupting %i", self.pid)
            await self._signal(signal.SIGINT)
            await self.wait_for_death(self.interrupt_timeout)

        # clean shutdown failed, use TERM
        status = await self.poll()
        if status is not None:
            return
        self.log.debug("Terminating %i", self.pid)
        await self._signal(signal.SIGTERM)
        await self.wait_for_death(self.term_timeout)

        # TERM failed, use KILL
        status = await self.poll()
        if status is not None:
            return
        self.log.debug("Killing %i", self.pid)
        await self._signal(signal.SIGKILL)
        await self.wait_for_death(self.kill_timeout)

        status = await self.poll()
        if status is None:
            # it all failed, zombie process
            self.log.warning("Process %i never died", self.pid)


class SimpleLocalProcessSpawner(LocalProcessSpawner):
    """
    A version of LocalProcessSpawner that doesn't require users to exist on
    the system beforehand.

    Only use this for testing.

    Note: DO NOT USE THIS FOR PRODUCTION USE CASES! It is very insecure, and
    provides absolutely no isolation between different users!
    """

    home_dir_template = Unicode(
        '/tmp/{username}',
        config=True,
        help="""
        Template to expand to set the user home.
        {username} is expanded to the jupyterhub username.
        """,
    )

    home_dir = Unicode(help="The home directory for the user")

    @default('home_dir')
    def _default_home_dir(self):
        return self.home_dir_template.format(username=self.user.name)

    def make_preexec_fn(self, name):
        home = self.home_dir

        def preexec():
            try:
                os.makedirs(home, 0o755, exist_ok=True)
                os.chdir(home)
            except Exception as e:
                self.log.exception("Error in preexec for %s", name)

        return preexec

    def user_env(self, env):
        env['USER'] = self.user.name
        env['HOME'] = self.home_dir
        env['SHELL'] = '/bin/bash'
        return env

    def move_certs(self, paths):
        """No-op for installing certs."""
        return paths
