"""HTTP Handlers for the hub server"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import re
from datetime import datetime, timedelta
from http.client import responses

from jinja2 import TemplateNotFound

from tornado.log import app_log
from tornado.httputil import url_concat
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler
from tornado import gen, web

from .. import orm
from ..spawner import LocalProcessSpawner
from ..utils import url_path_join

# pattern for the authentication token header
auth_header_pat = re.compile(r'^token\s+([^\s]+)$')

# mapping of reason: reason_message
reasons = {
    'timeout': "Failed to reach your server."
        "  Please try again later."
        "  Contact admin if the issue persists.",
    'error': "Failed to start your server.  Please contact admin.",
}

class BaseHandler(RequestHandler):
    """Base Handler class with access to common methods and properties."""

    @property
    def log(self):
        """I can't seem to avoid typing self.log"""
        return self.settings.get('log', app_log)

    @property
    def config(self):
        return self.settings.get('config', None)

    @property
    def base_url(self):
        return self.settings.get('base_url', '/')
    
    @property
    def version_hash(self):
        return self.settings.get('version_hash', '')
    
    @property
    def db(self):
        return self.settings['db']

    @property
    def hub(self):
        return self.settings['hub']
    
    @property
    def proxy(self):
        return self.settings['proxy']
    
    @property
    def authenticator(self):
        return self.settings.get('authenticator', None)

    def finish(self, *args, **kwargs):
        """Roll back any uncommitted transactions from the handler."""
        self.db.rollback()
        super().finish(*args, **kwargs)
    
    #---------------------------------------------------------------
    # Security policies
    #---------------------------------------------------------------
    
    @property
    def csp_report_uri(self):
        return self.settings.get('csp_report_uri',
            url_path_join(self.hub.server.base_url, 'security/csp-report')
        )
    
    @property
    def content_security_policy(self):
        """The default Content-Security-Policy header
        
        Can be overridden by defining Content-Security-Policy in settings['headers']
        """
        return '; '.join([
            "frame-ancestors 'self'",
            "report-uri " + self.csp_report_uri,
        ])
    
    def set_default_headers(self):
        """
        Set any headers passed as tornado_settings['headers'].

        By default sets Content-Security-Policy of frame-ancestors 'self'.
        """
        headers = self.settings.get('headers', {})
        headers.setdefault("Content-Security-Policy", self.content_security_policy)
        
        for header_name, header_content in headers.items():
            self.set_header(header_name, header_content)

    #---------------------------------------------------------------
    # Login and cookie-related
    #---------------------------------------------------------------

    @property
    def admin_users(self):
        return self.settings.setdefault('admin_users', set())
    
    @property
    def cookie_max_age_days(self):
        return self.settings.get('cookie_max_age_days', None)

    def get_current_user_token(self):
        """get_current_user from Authorization header token"""
        auth_header = self.request.headers.get('Authorization', '')
        match = auth_header_pat.match(auth_header)
        if not match:
            return None
        token = match.group(1)
        orm_token = orm.APIToken.find(self.db, token)
        if orm_token is None:
            return None
        else:
            return orm_token.user
    
    def _user_for_cookie(self, cookie_name, cookie_value=None):
        """Get the User for a given cookie, if there is one"""
        cookie_id = self.get_secure_cookie(
            cookie_name,
            cookie_value,
            max_age_days=self.cookie_max_age_days,
        )
        def clear():
            self.clear_cookie(cookie_name, path=self.hub.server.base_url)
        
        if cookie_id is None:
            if self.get_cookie(cookie_name):
                self.log.warn("Invalid or expired cookie token")
                clear()
            return
        cookie_id = cookie_id.decode('utf8', 'replace')
        user = self.db.query(orm.User).filter(orm.User.cookie_id==cookie_id).first()
        if user is None:
            self.log.warn("Invalid cookie token")
            # have cookie, but it's not valid. Clear it and start over.
            clear()
        return user
    
    def get_current_user_cookie(self):
        """get_current_user from a cookie token"""
        return self._user_for_cookie(self.hub.server.cookie_name)
    
    def get_current_user(self):
        """get current username"""
        user = self.get_current_user_token()
        if user is not None:
            return user
        return self.get_current_user_cookie()
    
    def find_user(self, name):
        """Get a user by name
        
        return None if no such user
        """
        return orm.User.find(self.db, name)

    def user_from_username(self, username):
        """Get ORM User for username"""
        user = self.find_user(username)
        if user is None:
            user = orm.User(name=username)
            self.db.add(user)
            self.db.commit()
        return user
    
    def clear_login_cookie(self, name=None):
        if name is None:
            user = self.get_current_user()
        else:
            user = self.find_user(name)
        if user and user.server:
            self.clear_cookie(user.server.cookie_name, path=user.server.base_url)
        self.clear_cookie(self.hub.server.cookie_name, path=self.hub.server.base_url)
    
    def set_server_cookie(self, user):
        """set the login cookie for the single-user server"""
        # tornado <4.2 have a bug that consider secure==True as soon as
        # 'secure' kwarg is passed to set_secure_cookie
        if  self.request.protocol == 'https':
            kwargs = {'secure':True}
        else:
            kwargs = {}
        self.set_secure_cookie(
            user.server.cookie_name,
            user.cookie_id,
            path=user.server.base_url,
            **kwargs
        )
    
    def set_hub_cookie(self, user):
        """set the login cookie for the Hub"""
        # tornado <4.2 have a bug that consider secure==True as soon as
        # 'secure' kwarg is passed to set_secure_cookie
        if  self.request.protocol == 'https':
            kwargs = {'secure':True}
        else:
            kwargs = {}
        self.set_secure_cookie(
            self.hub.server.cookie_name,
            user.cookie_id,
            path=self.hub.server.base_url,
            **kwargs
        )
    
    def set_login_cookie(self, user):
        """Set login cookies for the Hub and single-user server."""
        # create and set a new cookie token for the single-user server
        if user.server:
            self.set_server_cookie(user)
        
        # create and set a new cookie token for the hub
        if not self.get_current_user_cookie():
            self.set_hub_cookie(user)
    
    @gen.coroutine
    def authenticate(self, data):
        auth = self.authenticator
        if auth is not None:
            result = yield auth.authenticate(self, data)
            return result
        else:
            self.log.error("No authentication function, login is impossible!")


    #---------------------------------------------------------------
    # spawning-related
    #---------------------------------------------------------------

    @property
    def slow_spawn_timeout(self):
        return self.settings.get('slow_spawn_timeout', 10)

    @property
    def slow_stop_timeout(self):
        return self.settings.get('slow_stop_timeout', 10)

    @property
    def spawner_class(self):
        return self.settings.get('spawner_class', LocalProcessSpawner)

    @gen.coroutine
    def spawn_single_user(self, user):
        if user.spawn_pending:
            raise RuntimeError("Spawn already pending for: %s" % user.name)
        tic = IOLoop.current().time()
        
        f = user.spawn(
            spawner_class=self.spawner_class,
            base_url=self.base_url,
            hub=self.hub,
            config=self.config,
        )
        @gen.coroutine
        def finish_user_spawn(f=None):
            """Finish the user spawn by registering listeners and notifying the proxy.
            
            If the spawner is slow to start, this is passed as an async callback,
            otherwise it is called immediately.
            """
            if f and f.exception() is not None:
                # failed, don't add to the proxy
                return
            toc = IOLoop.current().time()
            self.log.info("User %s server took %.3f seconds to start", user.name, toc-tic)
            yield self.proxy.add_user(user)
            user.spawner.add_poll_callback(self.user_stopped, user)
        
        try:
            yield gen.with_timeout(timedelta(seconds=self.slow_spawn_timeout), f)
        except gen.TimeoutError:
            if user.spawn_pending:
                # hit timeout, but spawn is still pending
                self.log.warn("User %s server is slow to start", user.name)
                # schedule finish for when the user finishes spawning
                IOLoop.current().add_future(f, finish_user_spawn)
            else:
                raise
        else:
            yield finish_user_spawn()
    
    @gen.coroutine
    def user_stopped(self, user):
        """Callback that fires when the spawner has stopped"""
        status = yield user.spawner.poll()
        if status is None:
            status = 'unknown'
        self.log.warn("User %s server stopped, with exit code: %s",
            user.name, status,
        )
        yield self.proxy.delete_user(user)
        yield user.stop()
    
    @gen.coroutine
    def stop_single_user(self, user):
        if user.stop_pending:
            raise RuntimeError("Stop already pending for: %s" % user.name)
        tic = IOLoop.current().time()
        yield self.proxy.delete_user(user)
        f = user.stop()
        @gen.coroutine
        def finish_stop(f=None):
            """Finish the stop action by noticing that the user is stopped.
            
            If the spawner is slow to stop, this is passed as an async callback,
            otherwise it is called immediately.
            """
            if f and f.exception() is not None:
                # failed, don't do anything
                return
            toc = IOLoop.current().time()
            self.log.info("User %s server took %.3f seconds to stop", user.name, toc-tic)
        
        try:
            yield gen.with_timeout(timedelta(seconds=self.slow_stop_timeout), f)
        except gen.TimeoutError:
            if user.stop_pending:
                # hit timeout, but stop is still pending
                self.log.warn("User %s server is slow to stop", user.name)
                # schedule finish for when the server finishes stopping
                IOLoop.current().add_future(f, finish_stop)
            else:
                raise
        else:
            yield finish_stop()

    #---------------------------------------------------------------
    # template rendering
    #---------------------------------------------------------------

    def get_template(self, name):
        """Return the jinja template object for a given name"""
        return self.settings['jinja2_env'].get_template(name)

    def render_template(self, name, **ns):
        ns.update(self.template_namespace)
        template = self.get_template(name)
        return template.render(**ns)

    @property
    def template_namespace(self):
        user = self.get_current_user()
        return dict(
            base_url=self.hub.server.base_url,
            prefix=self.base_url,
            user=user,
            login_url=self.settings['login_url'],
            login_service=self.authenticator.login_service,
            logout_url=self.settings['logout_url'],
            static_url=self.static_url,
            version_hash=self.version_hash,
        )

    def write_error(self, status_code, **kwargs):
        """render custom error pages"""
        exc_info = kwargs.get('exc_info')
        message = ''
        status_message = responses.get(status_code, 'Unknown HTTP Error')
        if exc_info:
            exception = exc_info[1]
            # get the custom message, if defined
            try:
                message = exception.log_message % exception.args
            except Exception:
                pass

            # construct the custom reason, if defined
            reason = getattr(exception, 'reason', '')
            if reason:
                message = reasons.get(reason, reason)

        # build template namespace
        ns = dict(
            status_code=status_code,
            status_message=status_message,
            message=message,
            exception=exception,
        )

        self.set_header('Content-Type', 'text/html')
        # render the template
        try:
            html = self.render_template('%s.html' % status_code, **ns)
        except TemplateNotFound:
            self.log.debug("No template for %d", status_code)
            html = self.render_template('error.html', **ns)

        self.write(html)


class Template404(BaseHandler):
    """Render our 404 template"""
    def prepare(self):
        raise web.HTTPError(404)


class PrefixRedirectHandler(BaseHandler):
    """Redirect anything outside a prefix inside.
    
    Redirects /foo to /prefix/foo, etc.
    """
    def get(self):
        path = self.request.uri[len(self.base_url):]
        self.redirect(url_path_join(
            self.hub.server.base_url, path,
        ), permanent=False)


class UserSpawnHandler(BaseHandler):
    """Requests to /user/name handled by the Hub
    should result in spawning the single-user server and
    being redirected to the original.
    """
    @gen.coroutine
    def get(self, name):
        current_user = self.get_current_user()
        if current_user and current_user.name == name:
            # logged in, spawn the server
            if current_user.spawner:
                if current_user.spawn_pending:
                    # spawn has started, but not finished
                    html = self.render_template("spawn_pending.html", user=current_user)
                    self.finish(html)
                    return
                
                # spawn has supposedly finished, check on the status
                status = yield current_user.spawner.poll()
                if status is not None:
                    yield self.spawn_single_user(current_user)
            else:
                yield self.spawn_single_user(current_user)
            # set login cookie anew
            self.set_login_cookie(current_user)
            without_prefix = self.request.uri[len(self.hub.server.base_url):]
            target = url_path_join(self.base_url, without_prefix)
            self.redirect(target)
        else:
            # not logged in to the right user,
            # clear any cookies and reload (will redirect to login)
            self.clear_login_cookie()
            self.redirect(url_concat(
                self.settings['login_url'],
                {'next': self.request.uri,
            }))

class CSPReportHandler(BaseHandler):
    '''Accepts a content security policy violation report'''
    @web.authenticated
    def post(self):
        '''Log a content security policy violation report'''
        self.log.warn("Content security violation: %s",
                      self.request.body.decode('utf8', 'replace'))

default_handlers = [
    (r'/user/([^/]+)/?.*', UserSpawnHandler),
    (r'/security/csp-report', CSPReportHandler),
]
