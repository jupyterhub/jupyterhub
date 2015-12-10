"""Simple PAM authenticator"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

from grp import getgrnam
import pwd
from subprocess import check_call, check_output, CalledProcessError

from tornado import gen
import pamela

from traitlets.config import LoggingConfigurable
from traitlets import Bool, Set, Unicode, Any

from .handlers.login import LoginHandler
from .utils import url_path_join

class Authenticator(LoggingConfigurable):
    """A class for authentication.
    
    The API is one method, `authenticate`, a tornado gen.coroutine.
    """
    
    db = Any()
    admin_users = Set(config=True,
        help="""set of usernames of admin users

        If unspecified, only the user that launches the server will be admin.
        """
    )
    whitelist = Set(config=True,
        help="""Username whitelist.
        
        Use this to restrict which users can login.
        If empty, allow any user to attempt login.
        """
    )
    custom_html = Unicode('',
        help="""HTML login form for custom handlers.
        Override in form-based custom authenticators
        that don't use username+password,
        or need custom branding.
        """
    )
    login_service = Unicode('',
        help="""Name of the login service for external
        login services (e.g. 'GitHub').
        """
    )
    
    @gen.coroutine
    def authenticate(self, handler, data):
        """Authenticate a user with login form data.
        
        This must be a tornado gen.coroutine.
        It must return the username on successful authentication,
        and return None on failed authentication.
        """

    def pre_spawn_start(self, user, spawner):
        """Hook called before spawning a user's server.
        
        Can be used to do auth-related startup, e.g. opening PAM sessions.
        """
    
    def post_spawn_stop(self, user, spawner):
        """Hook called after stopping a user container.
        
        Can be used to do auth-related cleanup, e.g. closing PAM sessions.
        """
    
    def check_whitelist(self, user):
        """
        Return True if the whitelist is empty or user is in the whitelist.
        """
        # Parens aren't necessary here, but they make this easier to parse.
        return (not self.whitelist) or (user in self.whitelist)

    def add_user(self, user):
        """Add a new user
        
        By default, this just adds the user to the whitelist.
        
        Subclasses may do more extensive things,
        such as adding actual unix users.
        """
        if self.whitelist:
            self.whitelist.add(user.name)
    
    def delete_user(self, user):
        """Triggered when a user is deleted.
        
        Removes the user from the whitelist.
        """
        self.whitelist.discard(user.name)
    
    def login_url(self, base_url):
        """Override to register a custom login handler"""
        return url_path_join(base_url, 'login')
    
    def logout_url(self, base_url):
        """Override to register a custom logout handler"""
        return url_path_join(base_url, 'logout')
    
    def get_handlers(self, app):
        """Return any custom handlers the authenticator needs to register
        
        (e.g. for OAuth)
        """
        return [
            ('/login', LoginHandler),
        ]

class LocalAuthenticator(Authenticator):
    """Base class for Authenticators that work with local *ix users
    
    Checks for local users, and can attempt to create them if they exist.
    """
    
    create_system_users = Bool(False, config=True,
        help="""If a user is added that doesn't exist on the system,
        should I try to create the system user?
        """
    )
    system_user_home = Unicode('', config=True,
        help="""Specify root home directory for users if different from system default.
        
        Passed to `useradd -b`.
        If specified, when system users are created their home directories will be created in
        
            system_user_home/username
        
        Only has an effect when users are created with `create_system_users=True`.
        """
    )

    group_whitelist = Set(
        config=True,
        help="Automatically whitelist anyone in this group.",
    )

    def _group_whitelist_changed(self, name, old, new):
        if self.whitelist:
            self.log.warn(
                "Ignoring username whitelist because group whitelist supplied!"
            )

    def check_whitelist(self, username):
        if self.group_whitelist:
            return self.check_group_whitelist(username)
        else:
            return super().check_whitelist(username)

    def check_group_whitelist(self, username):
        if not self.group_whitelist:
            return False
        for grnam in self.group_whitelist:
            try:
                group = getgrnam(grnam)
            except KeyError:
                self.log.error('No such group: [%s]' % grnam)
                continue
            if username in group.gr_mem:
                return True
        return False

    @gen.coroutine
    def add_user(self, user):
        """Add a new user
        
        By default, this just adds the user to the whitelist.
        
        Subclasses may do more extensive things,
        such as adding actual unix users.
        """
        user_exists = yield gen.maybe_future(self.system_user_exists(user))
        if not user_exists:
            if self.create_system_users:
                yield gen.maybe_future(self.add_system_user(user))
            else:
                raise KeyError("User %s does not exist." % user.name)
        
        yield gen.maybe_future(super().add_user(user))
    
    @staticmethod
    def system_user_exists(user):
        """Check if the user exists on the system"""
        try:
            pwd.getpwnam(user.name)
        except KeyError:
            return False
        else:
            return True
    
    def add_system_user(self, user):
        """Create a new *ix user on the system. Works on FreeBSD and Linux, at least."""
        name = user.name
        for useradd in (
            ['pw', 'useradd', '-m'],
            ['useradd', '-m'],
        ):
            try:
                check_output(['which', useradd[0]])
            except CalledProcessError:
                continue
            else:
                break
        else:
            raise RuntimeError("I don't know how to add users on this system.")
        
        cmd = useradd
        if self.system_user_home:
            cmd = cmd + ['-b', self.system_user_home]
        check_call(cmd + [name])


class PAMAuthenticator(LocalAuthenticator):
    """Authenticate local *ix users with PAM"""
    encoding = Unicode('utf8', config=True,
        help="""The encoding to use for PAM"""
    )
    service = Unicode('login', config=True,
        help="""The PAM service to use for authentication."""
    )
    
    @gen.coroutine
    def authenticate(self, handler, data):
        """Authenticate with PAM, and return the username if login is successful.
    
        Return None otherwise.
        """
        username = data['username']
        if not self.check_whitelist(username):
            return
        try:
            pamela.authenticate(username, data['password'], service=self.service)
        except pamela.PAMError as e:
            if handler is not None:
                self.log.warn("PAM Authentication failed (@%s): %s", handler.request.remote_ip, e)
            else:
                self.log.warn("PAM Authentication failed: %s", e)
        else:
            return username
    
    def pre_spawn_start(self, user, spawner):
        """Open PAM session for user"""
        try:
            pamela.open_session(user.name, service=self.service)
        except pamela.PAMError as e:
            self.log.warn("Failed to open PAM session for %s: %s", user.name, e)
    
    def post_spawn_stop(self, user, spawner):
        """Close PAM session for user"""
        try:
            pamela.close_session(user.name, service=self.service)
        except pamela.PAMError as e:
            self.log.warn("Failed to close PAM session for %s: %s", user.name, e)
    
