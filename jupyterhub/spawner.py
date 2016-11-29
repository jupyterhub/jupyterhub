"""Class for spawning single-user notebook servers."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import errno
import os
import pipes
import pwd
import shutil
import signal
import sys
import grp
import warnings
from subprocess import Popen
from tempfile import mkdtemp

from tornado import gen
from tornado.ioloop import PeriodicCallback

from traitlets.config import LoggingConfigurable
from traitlets import (
    Any, Bool, Dict, Instance, Integer, Float, List, Unicode,
    validate,
)

from .traitlets import Command, MemorySpecification
from .utils import random_port


class Spawner(LoggingConfigurable):
    """
    Abstract base class for spawning single-user notebook servers.

    Subclass this, and override the following methods:

    - load_state
    - get_state
    - start
    - stop
    - poll

    An instance of a `Spawner` subclass is created for each user.
    """

    db = Any()
    user = Any()
    hub = Any()
    authenticator = Any()
    api_token = Unicode()

    ip = Unicode(
        '127.0.0.1',
        help="""
        The IP address (or hostname) the single-user server should listen on.

        The JupyterHub proxy implementation should be able to send packets to this interface.
        """
    ).tag(config=True)

    port = Integer(
        0,
        help="""
        The port for single-user servers to listen on.

        Defaults to `0`, which uses a randomly allocated port number each time.

        New in version 0.7.
        """
    )

    start_timeout = Integer(
        60,
        help="""
        Timeout (in seconds) before giving up on starting of single-user server.

        This is the timeout for start to return, not the timeout for the server to respond.
        Callers of spawner.start will assume that startup has failed if it takes longer than this.
        start should return when the server process is started and its location is known.
        """
    ).tag(config=True)

    http_timeout = Integer(
        30,
        help="""
        Timeout (in seconds) before giving up on a spawned HTTP server

        Once a server has successfully been spawned, this is the amount of time
        we wait before assuming that the server is unable to accept
        connections.
        """
    ).tag(config=True)

    poll_interval = Integer(
        30,
        help="""
        Interval (in seconds) on which to poll the spawner for single-user server's status.

        At every poll interval, each User's Spawner's `.poll` method is called, which checks
        if the single-user server is still running. If it isn't running, then JupyterHub modifies
        its own state accordingly and removes appropriate routes from the configurable proxy.
        """
    ).tag(config=True)

    _callbacks = List()
    _poll_callback = Any()

    debug = Bool(False,
        help="""
        Enable debug-logging of the single-user server.

        These logs will be sent to wherever the single-user server is configured to send its logs
        to (stderr by default). Your installation might need a log collection setup locally setup
        if you want to capture all single-user server logs in one place.
        """
    ).tag(config=True)

    options_form = Unicode(
        "",
        help="""
        An HTML form for options a user can specify on launching their server.
        The surrounding `<form>` element and the submit button are already provided.

        For example:

            Set your key:
            <input name="key" val="default_key"></input>
            <br>
            Choose a letter:
            <select name="letter" multiple="true">
              <option value="A">The letter A</option>
              <option value="B">The letter B</option>
            </select>

        The data from this form submission will be passed on to your spawner in `self.user_options`
    """).tag(config=True)

    def options_from_form(self, form_data):
        """Interpret HTTP form data
        
        Form data will always arrive as a dict of lists of strings.
        Override this function to understand single-values, numbers, etc.
        
        This should coerce form data into the structure expected by self.user_options,
        which must be a dict.
        
        Instances will receive this data on self.user_options, after passing through this function,
        prior to `Spawner.start`.
        """
        return form_data

    user_options = Dict(
        help="""
        Dict of user specified options specific to this spawned instance of the single-user server.

        These are usually provided by the form displayed to the user by setting `options_form`
        """)

    env_keep = List([
        'PATH',
        'PYTHONPATH',
        'CONDA_ROOT',
        'CONDA_DEFAULT_ENV',
        'VIRTUAL_ENV',
        'LANG',
        'LC_ALL',
    ],
        help="""
        Whitelist of environment variables for the single-user server to inherit from the JupyterHub process.

        This whitelist is used to ensure that sensitive information in the JupyterHub process's environment
        (such as `CONFIGPROXY_AUTH_TOKEN`) is not passed to the single-user server's process.
        """
    ).tag(config=True)

    env = Dict(help="""Deprecated: use Spawner.get_env or Spawner.environment

    - extend Spawner.get_env for adding required env in Spawner subclasses
    - Spawner.environment for config-specified env
    """)

    environment = Dict(
        help="""
        Extra environment variables to set for the single-user server's process.

        Environment variables that end up in the single-user server's process come from 3 sources:
          - This `environment` configurable
          - The JupyterHub process' environment variables that are whitelisted in `env_keep`
          - Variables to establish contact between the single-user notebook and the hub (such as JPY_API_TOKEN)

        The `enviornment` configurable should be set by JupyterHub administrators to add
        installation specific environment variables. It is a dict where the key is the name of the environment
        variable, and the value can be a string or a callable. If it is a callable, it will be called
        with one parameter (the spawner instance), and should return a string fairly quickly (no blocking
        operations please!).

        Note that the spawner class' interface is not guaranteed to be exactly same across upgrades,
        so if you are using the callable take care to verify it continues to work after upgrades!
        """
    ).tag(config=True)

    # FIXME: Add info about shell expansion here.
    cmd = Command(
        ['jupyterhub-singleuser'],
        help="""
        The command used for starting the single-user server.

        You can provide this as either a list or a string. Note that this should only contain
        the path to the script to start - extra arguments should be provided via `args`.

        This is usually set if you want to start the single-user server in a different python
        environment (with virtualenv/conda) than JupyterHub itself.
        """
    ).tag(config=True)

    # FIXME: Add info about shell expansion here.
    args = List(
        Unicode(),
        help="""
        Extra arguments to be passed to the single-user server.

        """
    ).tag(config=True)

    notebook_dir = Unicode(
        '',
        help="""
        Path to the notebook directory for the single-user server.

        The user will see a file listing of this directory when they start, and the Notebook
        interface itself will not allow browsing outside the contents of this directory (and its
        subdirectories) easily.

        `~` will be expanded to the home directory of the user, and {username} will be replaced
        with the name of the user.

        Note that this does *not* prevent users from accessing files outside of this path! They
        can do so with many other means.
        """
    ).tag(config=True)

    default_url = Unicode(
        '',
        help="""
        The URL the single-user server should start in.

        `{username}` will be expanded to the user's username

        Example uses:
        - You can set `notebook_dir` to `/` and `default_url` to `/home/{username}` to allow people to
          navigate the whole filesystem from their notebook, but still start in their home directory.
        - You can set this to `/lab` to have JupyterLab start by default, rather than Jupyter Notebook.
        """
    ).tag(config=True)

    @validate('notebook_dir', 'default_url')
    def _deprecate_percent_u(self, proposal):
        print(proposal)
        v = proposal['value']
        if '%U' in v:
            self.log.warning("%%U for username in %s is deprecated in JupyterHub 0.7, use {username}",
                proposal['trait'].name,
            )
            v = v.replace('%U', '{username}')
            self.log.warning("Converting %r to %r", proposal['value'], v)
        return v

    disable_user_config = Bool(
        False,
        help="""
        Disable per-user configuration of single-user servers.

        This prevents any config in users' $HOME directories from having an effect on their server.

        Note that this can be easily circumvented if the users can modify their python environment,
        as is the case when they have their own conda environments / virtualenvs / containers.
        """
    ).tag(config=True)

    mem_limit = MemorySpecification(
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

        This needs to be supported by your spawner for it to work.
        """
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

        This needs to be supported by your spawner for it to work.
        """
    ).tag(config=True)

    mem_guarantee = MemorySpecification(
        None,
        help="""
        Minimum number of bytes a single-user notebook server is guaranteed to have available.

        Allows the following suffixes:
          - K -> Kilobytes
          - M -> Megabytes
          - G -> Gigabytes
          - T -> Terabytes

        This needs to be supported by your spawner for it to work.
        """
    ).tag(config=True)

    cpu_guarantee = Float(
        None,
        allow_none=True,
        help="""
        Minimum number of cpu-cores a single-user notebook server is guaranteed to have available.

        If this value is set to 0.5, allows use of 50% of one CPU.
        If this value is set to 2, allows use of up to 2 CPUs.

        Note that this needs to be supported by your spawner for it to work.
        """
    ).tag(config=True)

    def __init__(self, **kwargs):
        super(Spawner, self).__init__(**kwargs)
        if self.user.state:
            self.load_state(self.user.state)
    
    def load_state(self, state):
        """load state from the database
        
        This is the extensible part of state.
        
        Override in a subclass if there is state to load.
        Should call `super`.
        
        See Also
        --------
        
        get_state, clear_state
        """
        pass
    
    def get_state(self):
        """store the state necessary for load_state
        
        A black box of extra state for custom spawners.
        Subclasses should call `super`.
        
        Returns
        -------
        
        state: dict
             a JSONable dict of state
        """
        state = {}
        return state
    
    def clear_state(self):
        """clear any state that should be cleared when the process stops
        
        State that should be preserved across server instances should not be cleared.
        
        Subclasses should call super, to ensure that state is properly cleared.
        """
        self.api_token = ''
    
    def get_env(self):
        """Return the environment dict to use for the Spawner.

        This applies things like `env_keep`, anything defined in `Spawner.environment`,
        and adds the API token to the env.

        Use this to access the env in Spawner.start to allow extension in subclasses.
        """
        env = {}
        if self.env:
            warnings.warn("Spawner.env is deprecated, found %s" % self.env, DeprecationWarning)
            env.update(self.env)
        
        for key in self.env_keep:
            if key in os.environ:
                env[key] = os.environ[key]

        # config overrides. If the value is a callable, it will be called with
        # one parameter - the current spawner instance - and the return value
        # will be assigned to the environment variable. This will be called at
        # spawn time.
        for key, value in self.environment.items():
            if callable(value):
                env[key] = value(self)
            else:
                env[key] = value

        env['JPY_API_TOKEN'] = self.api_token

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

        return env

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
        if self.user.server:
            d['base_url'] = self.user.server.base_url
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

    def get_args(self):
        """Return the arguments to be passed after self.cmd"""
        args = [
            '--user="%s"' % self.user.name,
            '--cookie-name="%s"' % self.user.server.cookie_name,
            '--base-url="%s"' % self.user.server.base_url,
            '--hub-host="%s"' % self.hub.host,
            '--hub-prefix="%s"' % self.hub.server.base_url,
            '--hub-api-url="%s"' % self.hub.api_url,
            ]
        if self.ip:
            args.append('--ip="%s"' % self.ip)

        if self.port:
            args.append('--port=%i' % self.port)
        elif self.user.server.port:
            self.log.warning("Setting port from user.server is deprecated as of JupyterHub 0.7.")
            args.append('--port=%i' % self.user.server.port)

        if self.notebook_dir:
            notebook_dir = self.format_string(self.notebook_dir)
            args.append('--notebook-dir="%s"' % notebook_dir)
        if self.default_url:
            default_url = self.format_string(self.default_url)
            args.append('--NotebookApp.default_url="%s"' % default_url)

        if self.debug:
            args.append('--debug')
        if self.disable_user_config:
            args.append('--disable-user-config')
        args.extend(self.args)
        return args
    
    @gen.coroutine
    def start(self):
        """Start the single-user server
        
        Returns:
        
        (ip, port): the ip, port where the Hub can connect to the server.
        
        .. versionchanged:: 0.7
            Return ip, port instead of setting on self.user.server directly.
        """
        raise NotImplementedError("Override in subclass. Must be a Tornado gen.coroutine.")
    
    @gen.coroutine
    def stop(self, now=False):
        """Stop the single-user process"""
        raise NotImplementedError("Override in subclass. Must be a Tornado gen.coroutine.")
    
    @gen.coroutine
    def poll(self):
        """Check if the single-user process is running

        returns:
        
        None, if single-user process is running.
        Exit status (0 if unknown), if it is not running.

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
        raise NotImplementedError("Override in subclass. Must be a Tornado gen.coroutine.")
    
    def add_poll_callback(self, callback, *args, **kwargs):
        """add a callback to fire when the subprocess stops
        
        as noticed by periodic poll_and_notify()
        """
        if args or kwargs:
            cb = callback
            callback = lambda : cb(*args, **kwargs)
        self._callbacks.append(callback)
    
    def stop_polling(self):
        """stop the periodic poll"""
        if self._poll_callback:
            self._poll_callback.stop()
            self._poll_callback = None
        
    def start_polling(self):
        """Start polling periodically
        
        callbacks registered via `add_poll_callback` will fire
        if/when the process stops.
        
        Explicit termination via the stop method will not trigger the callbacks.
        """
        if self.poll_interval <= 0:
            self.log.debug("Not polling subprocess")
            return
        else:
            self.log.debug("Polling subprocess every %is", self.poll_interval)
        
        self.stop_polling()
        
        self._poll_callback = PeriodicCallback(
            self.poll_and_notify,
            1e3 * self.poll_interval
        )
        self._poll_callback.start()

    @gen.coroutine
    def poll_and_notify(self):
        """Used as a callback to periodically poll the process,
        and notify any watchers
        """
        status = yield self.poll()
        if status is None:
            # still running, nothing to do here
            return
        
        self.stop_polling()
        
        for callback in self._callbacks:
            try:
                yield gen.maybe_future(callback())
            except Exception:
                self.log.exception("Unhandled error in poll callback for %s", self)
        return status
    
    death_interval = Float(0.1)
    @gen.coroutine
    def wait_for_death(self, timeout=10):
        """wait for the process to die, up to timeout seconds"""
        for i in range(int(timeout / self.death_interval)):
            status = yield self.poll()
            if status is not None:
                break
            else:
                yield gen.sleep(self.death_interval)

def _try_setcwd(path):
    """Try to set CWD, walking up and ultimately falling back to a temp dir"""
    while path != '/':
        try:
            os.chdir(path)
        except OSError as e:
            exc = e # break exception instance out of except scope
            print("Couldn't set CWD to %s (%s)" % (path, e), file=sys.stderr)
            path, _ = os.path.split(path)
        else:
            return
    print("Couldn't set CWD at all (%s), using temp dir" % exc, file=sys.stderr)
    td = mkdtemp()
    os.chdir(td)


def set_user_setuid(username):
    """return a preexec_fn for setting the user (via setuid) of a spawned process"""
    user = pwd.getpwnam(username)
    uid = user.pw_uid
    gid = user.pw_gid
    home = user.pw_dir
    gids = [ g.gr_gid for g in grp.getgrall() if username in g.gr_mem ]
    
    def preexec():
        # set the user and group
        os.setgid(gid)
        try:
            os.setgroups(gids)
        except Exception as e:
            print('Failed to set groups %s' % e, file=sys.stderr)
        os.setuid(uid)

        # start in the user's home dir
        _try_setcwd(home)
    
    return preexec


class LocalProcessSpawner(Spawner):
    """A Spawner that just uses Popen to start local processes as users.
    
    Requires users to exist on the local system.
    
    This is the default spawner for JupyterHub.
    """
    
    INTERRUPT_TIMEOUT = Integer(10,
        help="Seconds to wait for process to halt after SIGINT before proceeding to SIGTERM"
    ).tag(config=True)
    TERM_TIMEOUT = Integer(5,
        help="Seconds to wait for process to halt after SIGTERM before proceeding to SIGKILL"
    ).tag(config=True)
    KILL_TIMEOUT = Integer(5,
        help="Seconds to wait for process to halt after SIGKILL before giving up"
    ).tag(config=True)
    
    proc = Instance(Popen, allow_none=True)
    pid = Integer(0)
    
    def make_preexec_fn(self, name):
        return set_user_setuid(name)
    
    def load_state(self, state):
        """load pid from state"""
        super(LocalProcessSpawner, self).load_state(state)
        if 'pid' in state:
            self.pid = state['pid']
    
    def get_state(self):
        """add pid to state"""
        state = super(LocalProcessSpawner, self).get_state()
        if self.pid:
            state['pid'] = self.pid
        return state
    
    def clear_state(self):
        """clear pid state"""
        super(LocalProcessSpawner, self).clear_state()
        self.pid = 0
    
    def user_env(self, env):
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
        """Add user environment variables"""
        env = super().get_env()
        env = self.user_env(env)
        return env
    
    @gen.coroutine
    def start(self):
        """Start the process"""
        self.port = random_port()
        cmd = []
        env = self.get_env()

        cmd.extend(self.cmd)
        cmd.extend(self.get_args())

        self.log.info("Spawning %s", ' '.join(pipes.quote(s) for s in cmd))
        try:
            self.proc = Popen(cmd, env=env,
                preexec_fn=self.make_preexec_fn(self.user.name),
                start_new_session=True, # don't forward signals
            )
        except PermissionError:
            # use which to get abspath
            script = shutil.which(cmd[0]) or cmd[0]
            self.log.error("Permission denied trying to run %r. Does %s have access to this file?",
                script, self.user.name,
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
                self.user.server.ip = self.ip
            self.user.server.port = self.port
        return (self.ip or '127.0.0.1', self.port)

    @gen.coroutine
    def poll(self):
        """Poll the process"""
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
        
        # send signal 0 to check if PID exists
        # this doesn't work on Windows, but that's okay because we don't support Windows.
        alive = yield self._signal(0)
        if not alive:
            self.clear_state()
            return 0
        else:
            return None
    
    @gen.coroutine
    def _signal(self, sig):
        """simple implementation of signal, which we can use when we are using setuid (we are root)"""
        try:
            os.kill(self.pid, sig)
        except OSError as e:
            if e.errno == errno.ESRCH:
                return False # process is gone
            else:
                raise
        return True # process exists
    
    @gen.coroutine
    def stop(self, now=False):
        """stop the subprocess
        
        if `now`, skip waiting for clean shutdown
        """
        if not now:
            status = yield self.poll()
            if status is not None:
                return
            self.log.debug("Interrupting %i", self.pid)
            yield self._signal(signal.SIGINT)
            yield self.wait_for_death(self.INTERRUPT_TIMEOUT)
        
        # clean shutdown failed, use TERM
        status = yield self.poll()
        if status is not None:
            return
        self.log.debug("Terminating %i", self.pid)
        yield self._signal(signal.SIGTERM)
        yield self.wait_for_death(self.TERM_TIMEOUT)
        
        # TERM failed, use KILL
        status = yield self.poll()
        if status is not None:
            return
        self.log.debug("Killing %i", self.pid)
        yield self._signal(signal.SIGKILL)
        yield self.wait_for_death(self.KILL_TIMEOUT)

        status = yield self.poll()
        if status is None:
            # it all failed, zombie process
            self.log.warning("Process %i never died", self.pid)

