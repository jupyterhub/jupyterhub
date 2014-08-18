"""Class for spawning single-user notebook servers."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import errno
import os
import signal
import sys
import time
from subprocess import Popen

from tornado import gen

from IPython.config import LoggingConfigurable
from IPython.utils.traitlets import (
    Any, Dict, Instance, Integer, List, Unicode,
)


from .utils import random_port, wait_for_server


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
    
    env_prefix = Unicode('IPY_')
    def _env_key(self, d, key, value):
        d['%s%s' % (self.env_prefix, key)] = value
    
    env = Dict()
    def _env_default(self):
        env = os.environ.copy()
        self._env_key(env, 'COOKIE_SECRET', self.user.server.cookie_secret)
        self._env_key(env, 'API_TOKEN', self.api_token)
        return env
    
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
            '--hub-api-url=%s' % self.hub.api_host_url,
            ]

    def start(self):
        raise NotImplementedError("Override in subclass")
    
    def stop(self):
        raise NotImplementedError("Override in subclass")
    
    def poll(self):
        raise NotImplementedError("Override in subclass")


class PopenSpawner(Spawner):
    """A Spawner that just uses Popen to start local processes."""
    cmd = List(Unicode, config=True,
        help="""The command used for starting notebooks."""
    )
    def _cmd_default(self):
        # should have sudo -u self.user
        return [sys.executable, '-m', 'multiuser.singleuser']
    
    proc = Instance(Popen)
    pid = Integer()
    
    def load_state(self, state):
        self.pid = state['pid']
    
    def get_state(self):
        return dict(pid=self.pid)
    
    def start(self):
        self.user.server.port = random_port()
        cmd = self.cmd + self.get_args()
        
        self.log.info("Spawning %r", cmd)
        self.proc = Popen(cmd, env=self.env,
            # don't forward signals
            preexec_fn=os.setpgrp,
        )
        self.pid = self.proc.pid
    
    def poll(self):
        # if we started the process, poll with Popen
        if self.proc is not None:
            return self.proc.poll()
        
        # if we resumed from stored state,
        # we don't have the Popen handle anymore
        
        # this doesn't work on Windows.
        # multi-user doesn't support Windows.
        try:
            os.kill(self.pid, 0)
        except OSError as e:
            if e.errno == errno.ESRCH:
                # no such process, return exitcode == 0, since we don't know
                return 0
        else:
            # None indicates the process is running
            return None
    
    def _wait_for_death(self, timeout=10):
        """wait for the process to die, up to timeout seconds"""
        for i in range(int(timeout * 10)):
            if self.poll() is None:
                break
            else:
                time.sleep(0.1)
    
    def stop(self, now=False):
        """stop the subprocess"""
        if not now:
            # double-sigint to request clean shutdown
            os.kill(self.pid, signal.SIGINT)
            os.kill(self.pid, signal.SIGINT)
            self._wait_for_death(10)
        
        # clean shutdown failed, use TERM
        if self.poll() is None:
            os.kill(self.pid, signal.SIGTERM)
            self._wait_for_death(5)
        
        # TERM failed, use KILL
        if self.poll() is None:
            os.kill(self.pid, signal.SIGKILL)
            self._wait_for_death(5)
        
        # it all failed, zombie process
