"""Class for spawning single-user notebook servers."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import errno
import os
import pwd
import signal
from subprocess import Popen

from tornado import gen
from tornado.ioloop import IOLoop, PeriodicCallback

from IPython.config import LoggingConfigurable
from IPython.utils.traitlets import (
    Any, Bool, Dict, Enum, Instance, Integer, List, Unicode,
)

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
    
    user = Any()
    hub = Any()
    api_token = Unicode()
    
    poll_interval = Integer(30, config=True,
        help="""Interval (in seconds) on which to poll the spawner."""
    )
    _callbacks = List()
    _poll_callback = Any()
    
    debug = Bool(False, config=True,
        help="Enable debug-logging of the single-user server"
    )
    def _debug_changed(self, name, old, new):
        try:
            # remove --debug if False,
            # and avoid doubling it if True
            self.cmd.remove('--debug')
        except ValueError:
            pass
        if new:
            self.cmd.append('--debug')
    
    env_prefix = Unicode('JPY_')
    def _env_key(self, d, key, value):
        d['%s%s' % (self.env_prefix, key)] = value
    
    env = Dict()
    def _env_default(self):
        env = os.environ.copy()
        for key in ['HOME', 'USER', 'USERNAME', 'LOGNAME', 'LNAME']:
            env.pop(key, None)
        self._env_key(env, 'COOKIE_SECRET', self.user.server.cookie_secret)
        self._env_key(env, 'API_TOKEN', self.api_token)
        return env
    
    cmd = List(Unicode, default_value=['jupyterhub-singleuser'], config=True,
        help="""The command used for starting notebooks."""
    )
    
    @classmethod
    def fromJSON(cls, state, **kwargs):
        """Create a new instance, and load its JSON state
        
        state will be a dict, loaded from JSON in the database.
        """
        inst = cls(**kwargs)
        inst.load_state(state)
        return inst
    
    def load_state(self, state):
        """load state from the database
        
        This is the extensible part of state 
        
        Override in a subclass if there is state to load.
        
        See Also
        --------
        
        get_state
        """
        pass
    
    def get_state(self):
        """store the state necessary for load_state
        
        A black box of extra state for custom spawners
        
        Returns
        -------
        
        state: dict
             a JSONable dict of state
        """
        return dict(api_token=self.api_token)
    
    def get_args(self):
        """Return the arguments to be passed after self.cmd"""
        return [
            '--user=%s' % self.user.name,
            '--port=%i' % self.user.server.port,
            '--cookie-name=%s' % self.user.server.cookie_name,
            '--base-url=%s' % self.user.server.base_url,
            
            '--hub-prefix=%s' % self.hub.server.base_url,
            '--hub-api-url=%s' % self.hub.api_url,
            ]
    
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


def set_user_setuid(username):
    """return a preexec_fn for setting the user (via setuid) of a spawned process"""
    user = pwd.getpwnam(username)
    uid = user.pw_uid
    gid = user.pw_gid
    home = user.pw_dir
    
    def preexec():
        # don't forward signals
        os.setpgrp()
        
        # set the user and group
        os.setgid(gid)
        os.setuid(uid)

        # start in the user's home dir
        os.chdir(home)
    
    return preexec


def set_user_sudo(username):
    """return a preexec_fn for setting the user (assuming sudo is used for setting the user)"""
    user = pwd.getpwnam(username)
    home = user.pw_dir

    def preexec():
        # don't forward signals
        os.setpgrp()
        # start in the user's home dir
        os.chdir(home)

    return preexec


class LocalProcessSpawner(Spawner):
    """A Spawner that just uses Popen to start local processes."""
    
    INTERRUPT_TIMEOUT = Integer(10, config=True,
        help="Seconds to wait for process to halt after SIGINT before proceeding to SIGTERM"
    )
    TERM_TIMEOUT = Integer(5, config=True,
        help="Seconds to wait for process to halt after SIGTERM before proceeding to SIGKILL"
    )
    KILL_TIMEOUT = Integer(5, config=True,
        help="Seconds to wait for process to halt after SIGKILL before giving up"
    )
    
    proc = Instance(Popen)
    pid = Integer()
    sudo_args = List(['-n'], config=True,
        help="""arguments to be passed to sudo (in addition to -u [username])

        only used if set_user = sudo
        """
    )

    make_preexec_fn = Any(set_user_setuid)

    set_user = Enum(['sudo', 'setuid'], default_value='setuid', config=True,
        help="""scheme for setting the user of the spawned process

        'sudo' can be more prudently restricted,
        but 'setuid' is simpler for a server run as root
        """
    )
    def _set_user_changed(self, name, old, new):
        if new == 'sudo':
            self.make_preexec_fn = set_user_sudo
        elif new == 'setuid':
            self.make_preexec_fn = set_user_setuid
        else:
            raise ValueError("This should be impossible")
    
    def load_state(self, state):
        super(LocalProcessSpawner, self).load_state(state)
        self.pid = state['pid']
    
    def get_state(self):
        state = super(LocalProcessSpawner, self).get_state()
        state['pid'] = self.pid
        return state
    
    def sudo_cmd(self, user):
        return ['sudo', '-u', user.name] + self.sudo_args
    
    def user_env(self, env):
        if self.set_user == 'setuid':
            env['USER'] = self.user.name
            env['HOME'] = pwd.getpwnam(self.user.name).pw_dir
        return env

    @gen.coroutine
    def start(self):
        """Start the process"""
        self.user.server.port = random_port()
        cmd = []
        env = self.user_env(self.env)
        if self.set_user == 'sudo':
            cmd = self.sudo_cmd(self.user)
        
        cmd.extend(self.cmd)
        cmd.extend(self.get_args())
        
        self.log.info("Spawning %r", cmd)
        self.proc = Popen(cmd, env=env,
            preexec_fn=self.make_preexec_fn(self.user.name),
        )
        self.pid = self.proc.pid
        self.start_polling()
    
    @gen.coroutine
    def poll(self):
        """Poll the process"""
        # if we started the process, poll with Popen
        if self.proc is not None:
            raise gen.Return(self.proc.poll())
        
        # if we resumed from stored state,
        # we don't have the Popen handle anymore
        
        # this doesn't work on Windows, but that's okay because we don't support Windows.
        try:
            os.kill(self.pid, 0)
        except OSError as e:
            if e.errno == errno.ESRCH:
                # no such process, return exitcode == 0, since we don't know the exit status
                raise gen.Return(0)
        else:
            # None indicates the process is running
            raise gen.Return(None)
    
    @gen.coroutine
    def _wait_for_death(self, timeout=10):
        """wait for the process to die, up to timeout seconds"""
        for i in range(int(timeout * 10)):
            status = yield self.poll()
            if status is not None:
                break
            else:
                loop = IOLoop.current()
                yield gen.Task(loop.add_timeout, loop.time() + 0.1)
    
    @gen.coroutine
    def stop(self, now=False):
        """stop the subprocess
        
        if `now`, skip waiting for clean shutdown
        """
        self.stop_polling()
        if not now:
            # SIGINT to request clean shutdown
            self.log.debug("Interrupting %i", self.pid)
            try:
                os.kill(self.pid, signal.SIGINT)
            except OSError as e:
                if e.errno == errno.ESRCH:
                    return
            
            yield self._wait_for_death(self.INTERRUPT_TIMEOUT)
        
        # clean shutdown failed, use TERM
        status = yield self.poll()
        if status is None:
            self.log.debug("Terminating %i", self.pid)
            try:
                os.kill(self.pid, signal.SIGTERM)
            except OSError as e:
                if e.errno == errno.ESRCH:
                    return
            yield self._wait_for_death(self.TERM_TIMEOUT)
        
        # TERM failed, use KILL
        status = yield self.poll()
        if status is None:
            self.log.debug("Killing %i", self.pid)
            try:
                os.kill(self.pid, signal.SIGKILL)
            except OSError as e:
                if e.errno == errno.ESRCH:
                    return
            yield self._wait_for_death(self.KILL_TIMEOUT)

        status = yield self.poll()
        if status is None:
            # it all failed, zombie process
            self.log.warn("Process %i never died", self.pid)
    
