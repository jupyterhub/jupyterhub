"""Classes for managing users."""

import json
import os
import signal
import sys
import time
import uuid
from subprocess import Popen

import requests

from tornado.log import app_log

from IPython.utils.traitlets import Any, Unicode, Integer, Dict
from IPython.config import LoggingConfigurable

from .utils import random_port, wait_for_server

class UserSession(LoggingConfigurable):
    env_prefix = Unicode('IPY_')
    process = Any()
    port = Integer()
    user = Unicode()
    cookie_secret = Unicode()
    cookie_name = Unicode()
    def _cookie_name_default(self):
        return 'ipy-multiuser-%s' % self.user
    
    multiuser_prefix = Unicode()
    multiuser_api_url = Unicode()
    
    url_prefix = Unicode()
    def _url_prefix_default(self):
        return '/user/%s/' % self.user
    
    api_token = Unicode()
    def _api_token_default(self):
        return str(uuid.uuid4())
    
    cookie_token = Unicode()
    def _cookie_token_default(self):
        return str(uuid.uuid4())
    
    def _env_key(self, d, key, value):
        d['%s%s' % (self.env_prefix, key)] = value
    
    env = Dict()
    def _env_default(self):
        env = os.environ.copy()
        self._env_key(env, 'COOKIE_SECRET', self.cookie_secret)
        self._env_key(env, 'API_TOKEN', self.api_token)
        return env
    
    @property
    def auth_data(self):
        return dict(
            user=self.user,
        )
    
    def start(self):
        assert self.process is None or self.process.poll() is not None
        cmd = [sys.executable, '-m', 'multiuser.singleuser',
            '--user=%s' % self.user, '--port=%i' % self.port,
            '--cookie-name=%s' % self.cookie_name,
            '--multiuser-prefix=%s' % self.multiuser_prefix,
            '--multiuser-api-url=%s' % self.multiuser_api_url,
            '--base-url=%s' % self.url_prefix,
            ]
        app_log.info("Spawning: %s" % cmd)
        self.process = Popen(cmd, env=self.env,
            # don't forward signals:
            preexec_fn=os.setpgrp,
        )
    
    def running(self):
        if self.process is None:
            return False
        if self.process.poll() is not None:
            self.process = None
            return False
        return True
    
    def request_stop(self):
        if self.running():
            self.process.send_signal(signal.SIGINT)
            time.sleep(0.1)
        if self.running():
            self.process.send_signal(signal.SIGINT)
        
    def stop(self):
        for i in range(100):
            if self.running():
                time.sleep(0.1)
            else:
                break
        if self.running():
            self.process.terminate()


class UserManager(LoggingConfigurable):
    
    users = Dict()
    routes_t = Unicode('http://{ip}:{port}/api/routes{uri}')
    single_user_t = Unicode('http://{ip}:{port}')
    
    single_user_ip = Unicode('localhost')
    proxy_ip = Unicode('localhost')
    proxy_port = Integer(8001)
    
    proxy_auth_token = Unicode()
    def _proxy_auth_token_default(self):
        return str(uuid.uuid4())
    
    def get_session(self, user, **kwargs):
        if user not in self.users:
            kwargs['user'] = user
            self.users[user] = UserSession(**kwargs)
        return self.users[user]
            
    def spawn(self, user):
        session = self.get_session(user)
        if session.running():
            app_log.warn("User session %s already running", user)
            return
        session.port = port = random_port()
        session.start()
        
        r = requests.post(
            self.routes_t.format(
                ip=self.proxy_ip,
                port=self.proxy_port,
                uri=session.url_prefix,
            ),
            data=json.dumps(dict(
                target=self.single_user_t.format(
                    ip=self.single_user_ip,
                    port=port
                ),
                user=user,
            )),
            headers={'Authorization': "token %s" % self.proxy_auth_token},
        )
        wait_for_server(self.single_user_ip, port)
        r.raise_for_status()
    
    def user_for_api_token(self, token):
        """Get the user session object for a given API token"""
        for session in self.users.values():
            if session.api_token == token:
                return session
    
    def user_for_cookie_token(self, token):
        """Get the user session object for a given cookie token"""
        for session in self.users.values():
            if session.cookie_token == token:
                return session
    
    def shutdown(self, user):
        assert user in self.users
        session = self.users.pop(user)
        session.stop()
        r = requests.delete(self.routes_url,
            data=json.dumps(user=user, port=session.port),
        )
        r.raise_for_status()
    
    def cleanup(self):
        sessions = list(self.users.values())
        self.users = {}
        for session in sessions:
            self.log.info("Cleaning up %s's server" % session.user)
            session.request_stop()
        for i in range(100):
            if any([ session.running() for session in sessions ]):
                time.sleep(0.1)
            else:
                break
        for session in sessions:
            session.stop()
