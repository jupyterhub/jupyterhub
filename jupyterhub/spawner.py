"""Class for spawning single-user notebook servers."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import errno
import os
import pipes
import pwd
import signal
import sys
import grp
from subprocess import Popen
from tempfile import mkdtemp

from tornado import gen
from tornado.ioloop import IOLoop, PeriodicCallback

from traitlets.config import LoggingConfigurable
from traitlets import (
    Any, Bool, Dict, Instance, Integer, Float, List, Unicode,
)

from .traitlets import Command
from .utils import random_port

class Spawner(LoggingConfigurable):
    """Base class for spawning single-user notebook servers.
    
    Subclass this, and override the following methods:
    
    - load_state
    - get_state
    - start
    - stop
    - poll
    """
    
    db = Any()
    user = Any()
    hub = Any()
    authenticator = Any()
    api_token = Unicode()
    ip = Unicode('127.0.0.1', config=True,
        help="The IP address (or hostname) the single-user server should listen on"
    )
    start_timeout = Integer(60, config=True,
        help="""Timeout (in seconds) before giving up on the spawner.
        
        This is the timeout for start to return, not the timeout for the server to respond.
        Callers of spawner.start will assume that startup has failed if it takes longer than this.
        start should return when the server process is started and its location is known.
        """
    )

    http_timeout = Integer(
        30, config=True,
        help="""Timeout (in seconds) before giving up on a spawned HTTP server

        Once a server has successfully been spawned, this is the amount of time
        we wait before assuming that the server is unable to accept
        connections.
        """
    )

    poll_interval = Integer(30, config=True,
        help="""Interval (in seconds) on which to poll the spawner."""
    )
    _callbacks = List()
    _poll_callback = Any()
    
    debug = Bool(False, config=True,
        help="Enable debug-logging of the single-user server"
    )
    
    options_form = Unicode("", config=True, help="""
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
    """)

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
    
    user_options = Dict(help="This is where form-specified options ultimately end up.")
    
    env_keep = List([
        'PATH',
        'PYTHONPATH',
        'CONDA_ROOT',
        'CONDA_DEFAULT_ENV',
        'VIRTUAL_ENV',
        'LANG',
        'LC_ALL',
    ], config=True,
        help="Whitelist of environment variables for the subprocess to inherit"
    )
    env = Dict(config=True,
        help="Environment variables to load into the Spawner environment."
    )
    
    cmd = Command(['jupyterhub-singleuser'], config=True,
        help="""The command used for starting notebooks."""
    )
    args = List(Unicode, config=True,
        help="""Extra arguments to be passed to the single-user server"""
    )
    
    notebook_dir = Unicode('', config=True,
        help="""The notebook directory for the single-user server
        
        `~` will be expanded to the user's home directory
        `%U` will be expanded to the user's username
        """
    )

    default_url = Unicode('', config=True,
        help="""The default URL for the single-user server. 

        Can be used in conjunction with --notebook-dir=/ to enable 
        full filesystem traversal, while preserving user's homedir as
        landing page for notebook

        `%U` will be expanded to the user's username
        """
    )
    
    disable_user_config = Bool(False, config=True,
        help="""Disable per-user configuration of single-user servers.
        
        This prevents any config in users' $HOME directories
        from having an effect on their server.
        """
    )
    
    def __init__(self, **kwargs):
        super(Spawner, self).__init__(**kwargs)
        if self.user.state:
            self.load_state(self.user.state)
    
    def load_state(self, state):
        """load state from the database
        
        This is the extensible part of state
        
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

        This applies things like `env_keep`, anything defined in `Spawner.env`,
        and adds the API token to the env.

        Use this to access the env in Spawner.start to allow extension in subclasses.
        """
        env = self.env.copy()
        for key in self.env_keep:
            if key in os.environ:
                env[key] = os.environ[key]
        env['JPY_API_TOKEN'] = self.api_token
        return env
    
    def get_args(self):
        """Return the arguments to be passed after self.cmd"""
        args = [
            '--user=%s' % self.user.name,
            '--port=%i' % self.user.server.port,
            '--cookie-name=%s' % self.user.server.cookie_name,
            '--base-url=%s' % self.user.server.base_url,
            '--hub-host=%s' % self.hub.host,
            '--hub-prefix=%s' % self.hub.server.base_url,
            '--hub-api-url=%s' % self.hub.api_url,
            ]
        if self.ip:
            args.append('--ip=%s' % self.ip)
        if self.notebook_dir:
            self.notebook_dir = self.notebook_dir.replace("%U",self.user.name)
            args.append('--notebook-dir=%s' % self.notebook_dir)
        if self.default_url:
            self.default_url = self.default_url.replace("%U",self.user.name)
            args.append('--NotebookApp.default_url=%s' % self.default_url)

        if self.debug:
            args.append('--debug')
        if self.disable_user_config:
            args.append('--disable-user-config')
        args.extend(self.args)
        return args
    
    @gen.coroutine
    def start(self):
        """Start the single-user process"""
        raise NotImplementedError("Override in subclass. Must be a Tornado gen.coroutine.")
    
    @gen.coroutine
    def stop(self, now=False):
        """Stop the single-user process"""
        raise NotImplementedError("Override in subclass. Must be a Tornado gen.coroutine.")
    
    @gen.coroutine
    def poll(self):
        """Check if the single-user process is running

        return None if it is, an exit status (0 if unknown) if it is not.
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
        
        add_callback = IOLoop.current().add_callback
        for callback in self._callbacks:
            add_callback(callback)
    
    death_interval = Float(0.1)
    @gen.coroutine
    def wait_for_death(self, timeout=10):
        """wait for the process to die, up to timeout seconds"""
        loop = IOLoop.current()
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
    
    INTERRUPT_TIMEOUT = Integer(10, config=True,
        help="Seconds to wait for process to halt after SIGINT before proceeding to SIGTERM"
    )
    TERM_TIMEOUT = Integer(5, config=True,
        help="Seconds to wait for process to halt after SIGTERM before proceeding to SIGKILL"
    )
    KILL_TIMEOUT = Integer(5, config=True,
        help="Seconds to wait for process to halt after SIGKILL before giving up"
    )
    
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
        if self.ip:
            self.user.server.ip = self.ip
        self.user.server.port = random_port()
        cmd = []
        env = self.get_env()
        
        cmd.extend(self.cmd)
        cmd.extend(self.get_args())
        
        self.log.info("Spawning %s", ' '.join(pipes.quote(s) for s in cmd))
        self.proc = Popen(cmd, env=env,
            preexec_fn=self.make_preexec_fn(self.user.name),
            start_new_session=True, # don't forward signals
        )
        self.pid = self.proc.pid
    
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
            self.log.warn("Process %i never died", self.pid)
    
