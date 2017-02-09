"""Base Authenticator class and the default PAM Authenticator"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

from grp import getgrnam
import pipes
import pwd
import re
from shutil import which
import sys
from subprocess import Popen, PIPE, STDOUT

from tornado import gen
import pamela

from traitlets.config import LoggingConfigurable
from traitlets import Bool, Set, Unicode, Dict, Any, default, observe

from .handlers.login import LoginHandler
from .utils import url_path_join
from .traitlets import Command


class Authenticator(LoggingConfigurable):
    """Base class for implementing an authentication provider for JupyterHub"""

    db = Any()

    admin_users = Set(
        help="""
        Set of users that will have admin rights on this JupyterHub.

        Admin users have extra privilages:
         - Use the admin panel to see list of users logged in
         - Add / remove users in some authenticators
         - Restart / halt the hub
         - Start / stop users' single-user servers
         - Can access each individual users' single-user server (if configured)

        Admin access should be treated the same way root access is.

        Defaults to an empty set, in which case no user has admin access.
        """
    ).tag(config=True)

    whitelist = Set(
        help="""
        Whitelist of usernames that are allowed to log in.

        Use this with supported authenticators to restrict which users can log in. This is an
        additional whitelist that further restricts users, beyond whatever restrictions the
        authenticator has in place.

        If empty, does not perform any additional restriction.
        """
    ).tag(config=True)

    @observe('whitelist')
    def _check_whitelist(self, change):
        short_names = [name for name in change['new'] if len(name) <= 1]
        if short_names:
            sorted_names = sorted(short_names)
            single = ''.join(sorted_names)
            string_set_typo = "set('%s')" % single
            self.log.warning("whitelist contains single-character names: %s; did you mean set([%r]) instead of %s?",
                sorted_names[:8], single, string_set_typo,
            )

    custom_html = Unicode(
        help="""
        HTML form to be overridden by authenticators if they want a custom authentication form.

        Defaults to an empty string, which shows the default username/password form.
        """
    )

    login_service = Unicode(
        help="""
        Name of the login service that this authenticator is providing using to authenticate users.

        Example: GitHub, MediaWiki, Google, etc.

        Setting this value replaces the login form with a "Login with <login_service>" button.

        Any authenticator that redirects to an external service (e.g. using OAuth) should set this.
        """
    )

    username_pattern = Unicode(
        help="""
        Regular expression pattern that all valid usernames must match.

        If a username does not match the pattern specified here, authentication will not be attempted.

        If not set, allow any username.
        """
    ).tag(config=True)

    @observe('username_pattern')
    def _username_pattern_changed(self, change):
        if not change['new']:
            self.username_regex = None
        self.username_regex = re.compile(change['new'])

    username_regex = Any(
        help="""
        Compiled regex kept in sync with `username_pattern`
        """
    )

    def validate_username(self, username):
        """Validate a normalized username

        Return True if username is valid, False otherwise.
        """
        if not self.username_regex:
            return True
        return bool(self.username_regex.match(username))

    username_map = Dict(
        help="""Dictionary mapping authenticator usernames to JupyterHub users.

        Primarily used to normalize OAuth user names to local users.
        """
    ).tag(config=True)

    def normalize_username(self, username):
        """Normalize the given username and return it

        Override in subclasses if usernames need different normalization rules.

        The default attempts to lowercase the username and apply `username_map` if it is
        set.
        """
        username = username.lower()
        username = self.username_map.get(username, username)
        return username

    def check_whitelist(self, username):
        """Check if a username is allowed to authenticate based on whitelist configuration

        Return True if username is allowed, False otherwise.
        No whitelist means any username is allowed.

        Names are normalized *before* being checked against the whitelist.
        """
        if not self.whitelist:
            # No whitelist means any name is allowed
            return True
        return username in self.whitelist

    @gen.coroutine
    def get_authenticated_user(self, handler, data):
        """Authenticate the user who is attempting to log in

        Returns normalized username if successful, None otherwise.

        This calls `authenticate`, which should be overridden in subclasses,
        normalizes the username if any normalization should be done,
        and then validates the name in the whitelist.

        This is the outer API for authenticating a user.
        Subclasses should not need to override this method.

        The various stages can be overridden separately:
         - `authenticate` turns formdata into a username
         - `normalize_username` normalizes the username
         - `check_whitelist` checks against the user whitelist
        """
        username = yield self.authenticate(handler, data)
        if username is None:
            return
        username = self.normalize_username(username)
        if not self.validate_username(username):
            self.log.warning("Disallowing invalid username %r.", username)
            return

        whitelist_pass = yield gen.maybe_future(self.check_whitelist(username))
        if whitelist_pass:
            return username
        else:
            self.log.warning("User %r not in whitelist.", username)
            return

    @gen.coroutine
    def authenticate(self, handler, data):
        """Authenticate a user with login form data

        This must be a tornado gen.coroutine.
        It must return the username on successful authentication,
        and return None on failed authentication.

        Checking the whitelist is handled separately by the caller.

        Args:
            handler (tornado.web.RequestHandler): the current request handler
            data (dict): The formdata of the login form.
                         The default form has 'username' and 'password' fields.
        Returns:
            username (str or None): The username of the authenticated user,
            or None if Authentication failed
        """

    def pre_spawn_start(self, user, spawner):
        """Hook called before spawning a user's server

        Can be used to do auth-related startup, e.g. opening PAM sessions.
        """

    def post_spawn_stop(self, user, spawner):
        """Hook called after stopping a user container

        Can be used to do auth-related cleanup, e.g. closing PAM sessions.
        """

    def add_user(self, user):
        """Hook called when a user is added to JupyterHub

        This is called:
         - When a user first authenticates
         - When the hub restarts, for all users.

        This method may be a coroutine.

        By default, this just adds the user to the whitelist.

        Subclasses may do more extensive things, such as adding actual unix users,
        but they should call super to ensure the whitelist is updated.

        Note that this should be idempotent, since it is called whenever the hub restarts
        for all users.

        Args:
            user (User): The User wrapper object
        """
        if not self.validate_username(user.name):
            raise ValueError("Invalid username: %s" % user.name)
        if self.whitelist:
            self.whitelist.add(user.name)

    def delete_user(self, user):
        """Hook called when a user is deleted

        Removes the user from the whitelist.
        Subclasses should call super to ensure the whitelist is updated.

        Args:
            user (User): The User wrapper object
        """
        self.whitelist.discard(user.name)

    def login_url(self, base_url):
        """Override this when registering a custom login handler

        Generally used by authenticators that do not use simple form based authentication.

        The subclass overriding this is responsible for making sure there is a handler
        available to handle the URL returned from this method, using the `get_handlers`
        method.

        Args:
            base_url (str): the base URL of the Hub (e.g. /hub/)

        Returns:
            str: The login URL, e.g. '/hub/login'
        """
        return url_path_join(base_url, 'login')

    def logout_url(self, base_url):
        """Override when registering a custom logout handler

        The subclass overriding this is responsible for making sure there is a handler
        available to handle the URL returned from this method, using the `get_handlers`
        method.

        Args:
            base_url (str): the base URL of the Hub (e.g. /hub/)

        Returns:
            str: The logout URL, e.g. '/hub/logout'
        """
        return url_path_join(base_url, 'logout')

    def get_handlers(self, app):
        """Return any custom handlers the authenticator needs to register

        Used in conjugation with `login_url` and `logout_url`.

        Args:
            app (JupyterHub Application):
                the application object, in case it needs to be accessed for info.
        Returns:
            handlers (list):
                list of ``('/url', Handler)`` tuples passed to tornado.
                The Hub prefix is added to any URLs.
        """
        return [
            ('/login', LoginHandler),
        ]


class LocalAuthenticator(Authenticator):
    """Base class for Authenticators that work with local Linux/UNIX users

    Checks for local users, and can attempt to create them if they exist.
    """

    create_system_users = Bool(False,
        help="""
        If set to True, will attempt to create local system users if they do not exist already.

        Supports Linux and BSD variants only.
        """
    ).tag(config=True)

    add_user_cmd = Command(
        help="""
        The command to use for creating users as a list of strings

        For each element in the list, the string USERNAME will be replaced with
        the user's username. The username will also be appended as the final argument.

        For Linux, the default value is:

            ['adduser', '-q', '--gecos', '""', '--disabled-password']

        To specify a custom home directory, set this to:

            ['adduser', '-q', '--gecos', '""', '--home', '/customhome/USERNAME', '--disabled-password']

        This will run the command:

            adduser -q --gecos "" --home /customhome/river --disabled-password river

        when the user 'river' is created.
        """
    ).tag(config=True)

    @default('add_user_cmd')
    def _add_user_cmd_default(self):
        """Guess the most likely-to-work adduser command for each platform"""
        if sys.platform == 'darwin':
            raise ValueError("I don't know how to create users on OS X")
        elif which('pw'):
            # Probably BSD
            return ['pw', 'useradd', '-m']
        else:
            # This appears to be the Linux non-interactive adduser command:
            return ['adduser', '-q', '--gecos', '""', '--disabled-password']

    group_whitelist = Set(
        help="""
        Whitelist all users from this UNIX group.

        This makes the username whitelist ineffective.
        """
    ).tag(config=True)

    @observe('group_whitelist')
    def _group_whitelist_changed(self, change):
        """
        Log a warning if both group_whitelist and user whitelist are set.
        """
        if self.whitelist:
            self.log.warning(
                "Ignoring username whitelist because group whitelist supplied!"
            )

    def check_whitelist(self, username):
        if self.group_whitelist:
            return self.check_group_whitelist(username)
        else:
            return super().check_whitelist(username)

    def check_group_whitelist(self, username):
        """
        If group_whitelist is configured, check if authenticating user is part of group.
        """
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
        """Hook called whenever a new user is added

        If self.create_system_users, the user will attempt to be created if it doesn't exist.
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
        """Create a new local UNIX user on the system.

        Tested to work on FreeBSD and Linux, at least.
        """
        name = user.name
        cmd = [ arg.replace('USERNAME', name) for arg in self.add_user_cmd ] + [name]
        self.log.info("Creating user: %s", ' '.join(map(pipes.quote, cmd)))
        p = Popen(cmd, stdout=PIPE, stderr=STDOUT)
        p.wait()
        if p.returncode:
            err = p.stdout.read().decode('utf8', 'replace')
            raise RuntimeError("Failed to create system user %s: %s" % (name, err))


class PAMAuthenticator(LocalAuthenticator):
    """Authenticate local UNIX users with PAM"""

    encoding = Unicode('utf8',
        help="""
        The text encoding to use when communicating with PAM
        """
    ).tag(config=True)

    service = Unicode('login',
        help="""
        The name of the PAM service to use for authentication
        """
    ).tag(config=True)

    open_sessions = Bool(True,
        help="""
        Whether to open a new PAM session when spawners are started.

        This may trigger things like mounting shared filsystems,
        loading credentials, etc. depending on system configuration,
        but it does not always work.

        If any errors are encountered when opening/closing PAM sessions,
        this is automatically set to False.
        """
    ).tag(config=True)

    @gen.coroutine
    def authenticate(self, handler, data):
        """Authenticate with PAM, and return the username if login is successful.

        Return None otherwise.
        """
        username = data['username']
        try:
            pamela.authenticate(username, data['password'], service=self.service)
        except pamela.PAMError as e:
            if handler is not None:
                self.log.warning("PAM Authentication failed (%s@%s): %s", username, handler.request.remote_ip, e)
            else:
                self.log.warning("PAM Authentication failed: %s", e)
        else:
            return username

    def pre_spawn_start(self, user, spawner):
        """Open PAM session for user if so configured"""
        if not self.open_sessions:
            return
        try:
            pamela.open_session(user.name, service=self.service)
        except pamela.PAMError as e:
            self.log.warning("Failed to open PAM session for %s: %s", user.name, e)
            self.log.warning("Disabling PAM sessions from now on.")
            self.open_sessions = False

    def post_spawn_stop(self, user, spawner):
        """Close PAM session for user if we were configured to opened one"""
        if not self.open_sessions:
            return
        try:
            pamela.close_session(user.name, service=self.service)
        except pamela.PAMError as e:
            self.log.warning("Failed to close PAM session for %s: %s", user.name, e)
            self.log.warning("Disabling PAM sessions from now on.")
            self.open_sessions = False
