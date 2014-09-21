"""Class for spawning single-user notebook servers."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import errno
import os
import pwd
import signal
import time
from subprocess import Popen

from tornado import gen
from tornado.ioloop import IOLoop

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
        return {}
    
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


def set_user_setuid(username):
    """return a preexec_fn for setting the user (via setuid) of a spawned process"""
    user = pwd.getpwnam(username)
    uid = user.pw_uid
    gid = user.pw_gid
    home = user.pw_dir
    
    def preexec():
        # start in the user's home dir
        os.chdir(home)
        
        # don't forward signals
        os.setpgrp()
        
        # set the user and group
        os.setgid(gid)
        os.setuid(uid)
    
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
        self.pid = state['pid']
    
    def get_state(self):
        return dict(pid=self.pid)
    
    def sudo_cmd(self, user):
        return ['sudo', '-u', user.name] + self.sudo_args

    @gen.coroutine
    def start(self):
        """Start the process"""
        self.user.server.port = random_port()
        cmd = []
        if self.set_user == 'sudo':
            cmd = self.sudo_cmd(self.user)
        cmd.extend(self.cmd)
        cmd.extend(self.get_args())
        
        self.log.info("Spawning %r", cmd)
        self.proc = Popen(cmd, env=self.env,
            preexec_fn=self.make_preexec_fn(self.user.name),
        )
        self.pid = self.proc.pid
    
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
    
