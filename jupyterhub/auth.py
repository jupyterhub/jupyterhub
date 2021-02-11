"""Base Authenticator class and the default PAM Authenticator"""
# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.
import inspect
import pipes
import re
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from shutil import which
from subprocess import PIPE
from subprocess import Popen
from subprocess import STDOUT

try:
    import pamela
except Exception as e:
    pamela = None
    _pamela_error = e

from tornado.concurrent import run_on_executor

from traitlets.config import LoggingConfigurable
from traitlets import Bool, Integer, Set, Unicode, Dict, Any, default, observe

from .handlers.login import LoginHandler
from .utils import maybe_future, url_path_join
from .traitlets import Command


class Authenticator(LoggingConfigurable):
    """Base class for implementing an authentication provider for JupyterHub"""

    db = Any()

    enable_auth_state = Bool(
        False,
        config=True,
        help="""Enable persisting auth_state (if available).

        auth_state will be encrypted and stored in the Hub's database.
        This can include things like authentication tokens, etc.
        to be passed to Spawners as environment variables.

        Encrypting auth_state requires the cryptography package.

        Additionally, the JUPYTERHUB_CRYPT_KEY environment variable must
        contain one (or more, separated by ;) 32B encryption keys.
        These can be either base64 or hex-encoded.

        If encryption is unavailable, auth_state cannot be persisted.

        New in JupyterHub 0.8
        """,
    )

    auth_refresh_age = Integer(
        300,
        config=True,
        help="""The max age (in seconds) of authentication info
        before forcing a refresh of user auth info.

        Refreshing auth info allows, e.g. requesting/re-validating auth tokens.

        See :meth:`.refresh_user` for what happens when user auth info is refreshed
        (nothing by default).
        """,
    )

    refresh_pre_spawn = Bool(
        False,
        config=True,
        help="""Force refresh of auth prior to spawn.

        This forces :meth:`.refresh_user` to be called prior to launching
        a server, to ensure that auth state is up-to-date.

        This can be important when e.g. auth tokens that may have expired
        are passed to the spawner via environment variables from auth_state.

        If refresh_user cannot refresh the user auth data,
        launch will fail until the user logs in again.
        """,
    )

    admin_users = Set(
        help="""
        Set of users that will have admin rights on this JupyterHub.

        Admin users have extra privileges:
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
        help="Deprecated, use `Authenticator.allowed_users`",
        config=True,
    )

    allowed_users = Set(
        help="""
        Set of usernames that are allowed to log in.

        Use this with supported authenticators to restrict which users can log in. This is an
        additional list that further restricts users, beyond whatever restrictions the
        authenticator has in place.

        If empty, does not perform any additional restriction.

        .. versionchanged:: 1.2
            `Authenticator.whitelist` renamed to `allowed_users`
        """
    ).tag(config=True)

    blocked_users = Set(
        help="""
        Set of usernames that are not allowed to log in.

        Use this with supported authenticators to restrict which users can not log in. This is an
        additional block list that further restricts users, beyond whatever restrictions the
        authenticator has in place.

        If empty, does not perform any additional restriction.

        .. versionadded: 0.9

        .. versionchanged:: 1.2
            `Authenticator.blacklist` renamed to `blocked_users`
        """
    ).tag(config=True)

    _deprecated_aliases = {
        "whitelist": ("allowed_users", "1.2"),
        "blacklist": ("blocked_users", "1.2"),
    }

    @observe(*list(_deprecated_aliases))
    def _deprecated_trait(self, change):
        """observer for deprecated traits"""
        old_attr = change.name
        new_attr, version = self._deprecated_aliases.get(old_attr)
        new_value = getattr(self, new_attr)
        if new_value != change.new:
            # only warn if different
            # protects backward-compatible config from warnings
            # if they set the same value under both names
            self.log.warning(
                "{cls}.{old} is deprecated in JupyterHub {version}, use {cls}.{new} instead".format(
                    cls=self.__class__.__name__,
                    old=old_attr,
                    new=new_attr,
                    version=version,
                )
            )
            setattr(self, new_attr, change.new)

    @observe('allowed_users')
    def _check_allowed_users(self, change):
        short_names = [name for name in change['new'] if len(name) <= 1]
        if short_names:
            sorted_names = sorted(short_names)
            single = ''.join(sorted_names)
            string_set_typo = "set('%s')" % single
            self.log.warning(
                "Allowed set contains single-character names: %s; did you mean set([%r]) instead of %s?",
                sorted_names[:8],
                single,
                string_set_typo,
            )

    custom_html = Unicode(
        help="""
        HTML form to be overridden by authenticators if they want a custom authentication form.

        Defaults to an empty string, which shows the default username/password form.
        """
    )

    def get_custom_html(self, base_url):
        """Get custom HTML for the authenticator.

        .. versionadded: 1.4
        """
        return self.custom_html

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
        if '/' in username:
            # / is not allowed in usernames
            return False
        if not username:
            # empty usernames are not allowed
            return False
        if not self.username_regex:
            return True
        return bool(self.username_regex.match(username))

    username_map = Dict(
        help="""Dictionary mapping authenticator usernames to JupyterHub users.

        Primarily used to normalize OAuth user names to local users.
        """
    ).tag(config=True)

    delete_invalid_users = Bool(
        False,
        config=True,
        help="""Delete any users from the database that do not pass validation

        When JupyterHub starts, `.add_user` will be called
        on each user in the database to verify that all users are still valid.

        If `delete_invalid_users` is True,
        any users that do not pass validation will be deleted from the database.
        Use this if users might be deleted from an external system,
        such as local user accounts.

        If False (default), invalid users remain in the Hub's database
        and a warning will be issued.
        This is the default to avoid data loss due to config changes.
        """,
    )

    post_auth_hook = Any(
        config=True,
        help="""
        An optional hook function that you can implement to do some
        bootstrapping work during authentication. For example, loading user account
        details from an external system.

        This function is called after the user has passed all authentication checks
        and is ready to successfully authenticate. This function must return the
        authentication dict reguardless of changes to it.

        This maybe a coroutine.

        .. versionadded: 1.0

        Example::

            import os, pwd
            def my_hook(authenticator, handler, authentication):
                user_data = pwd.getpwnam(authentication['name'])
                spawn_data = {
                    'pw_data': user_data
                    'gid_list': os.getgrouplist(authentication['name'], user_data.pw_gid)
                }

                if authentication['auth_state'] is None:
                    authentication['auth_state'] = {}
                authentication['auth_state']['spawn_data'] = spawn_data

                return authentication

            c.Authenticator.post_auth_hook = my_hook

        """,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._init_deprecated_methods()

    def _init_deprecated_methods(self):
        # handles deprecated signature *and* name
        # with correct subclass override priority!
        for old_name, new_name in (
            ('check_whitelist', 'check_allowed'),
            ('check_blacklist', 'check_blocked_users'),
            ('check_group_whitelist', 'check_allowed_groups'),
        ):
            old_method = getattr(self, old_name, None)
            if old_method is None:
                # no such method (check_group_whitelist is optional)
                continue

            # allow old name to have higher priority
            # if and only if it's defined in a later subclass
            # than the new name
            for cls in self.__class__.mro():
                has_old_name = old_name in cls.__dict__
                has_new_name = new_name in cls.__dict__
                if has_new_name:
                    break
                if has_old_name and not has_new_name:
                    warnings.warn(
                        "{0}.{1} should be renamed to {0}.{2} for JupyterHub >= 1.2".format(
                            cls.__name__, old_name, new_name
                        ),
                        DeprecationWarning,
                    )
                    # use old name instead of new
                    # if old name is overridden in subclass
                    def _new_calls_old(old_name, *args, **kwargs):
                        return getattr(self, old_name)(*args, **kwargs)

                    setattr(self, new_name, partial(_new_calls_old, old_name))
                    break

            # deprecate pre-1.0 method signatures
            signature = inspect.signature(old_method)
            if 'authentication' not in signature.parameters and not any(
                param.kind == inspect.Parameter.VAR_KEYWORD
                for param in signature.parameters.values()
            ):
                # adapt to pre-1.0 signature for compatibility
                warnings.warn(
                    """
                    {0}.{1} does not support the authentication argument,
                    added in JupyterHub 1.0. and is renamed to {2} in JupyterHub 1.2.

                    It should have the signature:

                    def {2}(self, username, authentication=None):
                        ...

                    Adapting for compatibility.
                    """.format(
                        self.__class__.__name__, old_name, new_name
                    ),
                    DeprecationWarning,
                )

                def wrapped_method(
                    original_method, username, authentication=None, **kwargs
                ):
                    return original_method(username, **kwargs)

                setattr(self, old_name, partial(wrapped_method, old_method))

    async def run_post_auth_hook(self, handler, authentication):
        """
        Run the post_auth_hook if defined

        .. versionadded: 1.0

        Args:
            handler (tornado.web.RequestHandler): the current request handler
            authentication (dict): User authentication data dictionary. Contains the
                username ('name'), admin status ('admin'), and auth state dictionary ('auth_state').
        Returns:
            Authentication (dict):
                The hook must always return the authentication dict
        """
        if self.post_auth_hook is not None:
            authentication = await maybe_future(
                self.post_auth_hook(self, handler, authentication)
            )
        return authentication

    def normalize_username(self, username):
        """Normalize the given username and return it

        Override in subclasses if usernames need different normalization rules.

        The default attempts to lowercase the username and apply `username_map` if it is
        set.
        """
        username = username.lower()
        username = self.username_map.get(username, username)
        return username

    def check_allowed(self, username, authentication=None):
        """Check if a username is allowed to authenticate based on configuration

        Return True if username is allowed, False otherwise.
        No allowed_users set means any username is allowed.

        Names are normalized *before* being checked against the allowed set.

        .. versionchanged:: 1.0
            Signature updated to accept authentication data and any future changes

        .. versionchanged:: 1.2
            Renamed check_whitelist to check_allowed
        """
        if not self.allowed_users:
            # No allowed set means any name is allowed
            return True
        return username in self.allowed_users

    def check_blocked_users(self, username, authentication=None):
        """Check if a username is blocked to authenticate based on Authenticator.blocked configuration

        Return True if username is allowed, False otherwise.
        No block list means any username is allowed.

        Names are normalized *before* being checked against the block list.

        .. versionadded: 0.9

        .. versionchanged:: 1.0
            Signature updated to accept authentication data as second argument

        .. versionchanged:: 1.2
            Renamed check_blacklist to check_blocked_users
        """
        if not self.blocked_users:
            # No block list means any name is allowed
            return True
        return username not in self.blocked_users

    async def get_authenticated_user(self, handler, data):
        """Authenticate the user who is attempting to log in

        Returns user dict if successful, None otherwise.

        This calls `authenticate`, which should be overridden in subclasses,
        normalizes the username if any normalization should be done,
        and then validates the name in the allowed set.

        This is the outer API for authenticating a user.
        Subclasses should not override this method.

        The various stages can be overridden separately:
         - `authenticate` turns formdata into a username
         - `normalize_username` normalizes the username
         - `check_allowed` checks against the allowed usernames

        .. versionchanged:: 0.8
            return dict instead of username
        """
        authenticated = await maybe_future(self.authenticate(handler, data))
        if authenticated is None:
            return
        if isinstance(authenticated, dict):
            if 'name' not in authenticated:
                raise ValueError("user missing a name: %r" % authenticated)
        else:
            authenticated = {'name': authenticated}
        authenticated.setdefault('auth_state', None)
        # Leave the default as None, but reevaluate later post-allowed-check
        authenticated.setdefault('admin', None)

        # normalize the username
        authenticated['name'] = username = self.normalize_username(
            authenticated['name']
        )
        if not self.validate_username(username):
            self.log.warning("Disallowing invalid username %r.", username)
            return

        blocked_pass = await maybe_future(
            self.check_blocked_users(username, authenticated)
        )
        allowed_pass = await maybe_future(self.check_allowed(username, authenticated))

        if blocked_pass:
            pass
        else:
            self.log.warning("User %r blocked. Stop authentication", username)
            return

        if allowed_pass:
            if authenticated['admin'] is None:
                authenticated['admin'] = await maybe_future(
                    self.is_admin(handler, authenticated)
                )

            authenticated = await self.run_post_auth_hook(handler, authenticated)

            return authenticated
        else:
            self.log.warning("User %r not allowed.", username)
            return

    async def refresh_user(self, user, handler=None):
        """Refresh auth data for a given user

        Allows refreshing or invalidating auth data.

        Only override if your authenticator needs
        to refresh its data about users once in a while.

        .. versionadded: 1.0

        Args:
            user (User): the user to refresh
            handler (tornado.web.RequestHandler or None): the current request handler
        Returns:
            auth_data (bool or dict):
                Return **True** if auth data for the user is up-to-date
                and no updates are required.

                Return **False** if the user's auth data has expired,
                and they should be required to login again.

                Return a **dict** of auth data if some values should be updated.
                This dict should have the same structure as that returned
                by :meth:`.authenticate()` when it returns a dict.
                Any fields present will refresh the value for the user.
                Any fields not present will be left unchanged.
                This can include updating `.admin` or `.auth_state` fields.
        """
        return True

    def is_admin(self, handler, authentication):
        """Authentication helper to determine a user's admin status.

        .. versionadded: 1.0

        Args:
            handler (tornado.web.RequestHandler): the current request handler
            authentication: The authetication dict generated by `authenticate`.
        Returns:
            admin_status (Bool or None):
                The admin status of the user, or None if it could not be
                determined or should not change.
        """
        return True if authentication['name'] in self.admin_users else None

    async def authenticate(self, handler, data):
        """Authenticate a user with login form data

        This must be a coroutine.

        It must return the username on successful authentication,
        and return None on failed authentication.

        Checking allowed_users/blocked_users is handled separately by the caller.

        .. versionchanged:: 0.8
            Allow `authenticate` to return a dict containing auth_state.

        Args:
            handler (tornado.web.RequestHandler): the current request handler
            data (dict): The formdata of the login form.
                         The default form has 'username' and 'password' fields.
        Returns:
            user (str or dict or None):
                The username of the authenticated user,
                or None if Authentication failed.

                The Authenticator may return a dict instead, which MUST have a
                key `name` holding the username, and MAY have two optional keys
                set: `auth_state`, a dictionary of of auth state that will be
                persisted; and `admin`, the admin setting value for the user.
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

        By default, this just adds the user to the allowed_users set.

        Subclasses may do more extensive things, such as adding actual unix users,
        but they should call super to ensure the allowed_users set is updated.

        Note that this should be idempotent, since it is called whenever the hub restarts
        for all users.

        Args:
            user (User): The User wrapper object
        """
        if not self.validate_username(user.name):
            raise ValueError("Invalid username: %s" % user.name)
        if self.allowed_users:
            self.allowed_users.add(user.name)

    def delete_user(self, user):
        """Hook called when a user is deleted

        Removes the user from the allowed_users set.
        Subclasses should call super to ensure the allowed_users set is updated.

        Args:
            user (User): The User wrapper object
        """
        self.allowed_users.discard(user.name)

    auto_login = Bool(
        False,
        config=True,
        help="""Automatically begin the login process

        rather than starting with a "Login with..." link at `/hub/login`

        To work, `.login_url()` must give a URL other than the default `/hub/login`,
        such as an oauth handler or another automatic login handler,
        registered with `.get_handlers()`.

        .. versionadded:: 0.8
        """,
    )

    def login_url(self, base_url):
        """Override this when registering a custom login handler

        Generally used by authenticators that do not use simple form-based authentication.

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
        return [('/login', LoginHandler)]


def _deprecated_method(old_name, new_name, version):
    """Create a deprecated method wrapper for a deprecated method name"""

    def deprecated(self, *args, **kwargs):
        warnings.warn(
            (
                "{cls}.{old_name} is deprecated in JupyterHub {version}."
                " Please use {cls}.{new_name} instead."
            ).format(
                cls=self.__class__.__name__,
                old_name=old_name,
                new_name=new_name,
                version=version,
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        old_method = getattr(self, new_name)
        return old_method(*args, **kwargs)

    return deprecated


import types

# deprecate white/blacklist method names
for _old_name, _new_name, _version in [
    ("check_whitelist", "check_allowed", "1.2"),
    ("check_blacklist", "check_blocked_users", "1.2"),
]:
    setattr(
        Authenticator,
        _old_name,
        _deprecated_method(_old_name, _new_name, _version),
    )


class LocalAuthenticator(Authenticator):
    """Base class for Authenticators that work with local Linux/UNIX users

    Checks for local users, and can attempt to create them if they exist.
    """

    create_system_users = Bool(
        False,
        help="""
        If set to True, will attempt to create local system users if they do not exist already.

        Supports Linux and BSD variants only.
        """,
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

    uids = Dict(
        help="""
        Dictionary of uids to use at user creation time.
        This helps ensure that users created from the database
        get the same uid each time they are created
        in temporary deployments or containers.
        """
    ).tag(config=True)

    group_whitelist = Set(
        help="""DEPRECATED: use allowed_groups""",
    ).tag(config=True)

    allowed_groups = Set(
        help="""
        Allow login from all users in these UNIX groups.

        If set, allowed username set is ignored.
        """
    ).tag(config=True)

    @observe('allowed_groups')
    def _allowed_groups_changed(self, change):
        """Log a warning if mutually exclusive user and group allowed sets are specified."""
        if self.allowed_users:
            self.log.warning(
                "Ignoring Authenticator.allowed_users set because Authenticator.allowed_groups supplied!"
            )

    def check_allowed(self, username, authentication=None):
        if self.allowed_groups:
            return self.check_allowed_groups(username, authentication)
        else:
            return super().check_allowed(username, authentication)

    def check_allowed_groups(self, username, authentication=None):
        """
        If allowed_groups is configured, check if authenticating user is part of group.
        """
        if not self.allowed_groups:
            return False
        for grnam in self.allowed_groups:
            try:
                group = self._getgrnam(grnam)
            except KeyError:
                self.log.error('No such group: [%s]' % grnam)
                continue
            if username in group.gr_mem:
                return True
        return False

    async def add_user(self, user):
        """Hook called whenever a new user is added

        If self.create_system_users, the user will attempt to be created if it doesn't exist.
        """
        user_exists = await maybe_future(self.system_user_exists(user))
        if not user_exists:
            if self.create_system_users:
                await maybe_future(self.add_system_user(user))
            else:
                raise KeyError(
                    "User {} does not exist on the system."
                    " Set LocalAuthenticator.create_system_users=True"
                    " to automatically create system users from jupyterhub users.".format(
                        user.name
                    )
                )

        await maybe_future(super().add_user(user))

    @staticmethod
    def _getgrnam(name):
        """Wrapper function to protect against `grp` not being available
        on Windows
        """
        import grp

        return grp.getgrnam(name)

    @staticmethod
    def _getpwnam(name):
        """Wrapper function to protect against `pwd` not being available
        on Windows
        """
        import pwd

        return pwd.getpwnam(name)

    @staticmethod
    def _getgrouplist(name, group):
        """Wrapper function to protect against `os._getgrouplist` not being available
        on Windows
        """
        import os

        return os.getgrouplist(name, group)

    def system_user_exists(self, user):
        """Check if the user exists on the system"""
        try:
            self._getpwnam(user.name)
        except KeyError:
            return False
        else:
            return True

    def add_system_user(self, user):
        """Create a new local UNIX user on the system.

        Tested to work on FreeBSD and Linux, at least.
        """
        name = user.name
        cmd = [arg.replace('USERNAME', name) for arg in self.add_user_cmd]
        try:
            uid = self.uids[name]
            cmd += ['--uid', '%d' % uid]
        except KeyError:
            self.log.debug("No UID for user %s" % name)
        cmd += [name]
        self.log.info("Creating user: %s", ' '.join(map(pipes.quote, cmd)))
        p = Popen(cmd, stdout=PIPE, stderr=STDOUT)
        p.wait()
        if p.returncode:
            err = p.stdout.read().decode('utf8', 'replace')
            raise RuntimeError("Failed to create system user %s: %s" % (name, err))


class PAMAuthenticator(LocalAuthenticator):
    """Authenticate local UNIX users with PAM"""

    # run PAM in a thread, since it can be slow
    executor = Any()

    @default('executor')
    def _default_executor(self):
        return ThreadPoolExecutor(1)

    encoding = Unicode(
        'utf8',
        help="""
        The text encoding to use when communicating with PAM
        """,
    ).tag(config=True)

    service = Unicode(
        'login',
        help="""
        The name of the PAM service to use for authentication
        """,
    ).tag(config=True)

    open_sessions = Bool(
        True,
        help="""
        Whether to open a new PAM session when spawners are started.

        This may trigger things like mounting shared filsystems,
        loading credentials, etc. depending on system configuration,
        but it does not always work.

        If any errors are encountered when opening/closing PAM sessions,
        this is automatically set to False.
        """,
    ).tag(config=True)

    check_account = Bool(
        True,
        help="""
        Whether to check the user's account status via PAM during authentication.

        The PAM account stack performs non-authentication based account 
        management. It is typically used to restrict/permit access to a 
        service and this step is needed to access the host's user access control.

        Disabling this can be dangerous as authenticated but unauthorized users may
        be granted access and, therefore, arbitrary execution on the system.
        """,
    ).tag(config=True)

    admin_groups = Set(
        help="""
        Authoritative list of user groups that determine admin access.
        Users not in these groups can still be granted admin status through admin_users.

        allowed/blocked rules still apply.
        """
    ).tag(config=True)

    pam_normalize_username = Bool(
        False,
        help="""
        Round-trip the username via PAM lookups to make sure it is unique

        PAM can accept multiple usernames that map to the same user,
        for example DOMAIN\\username in some cases.  To prevent this,
        convert username into uid, then back to uid to normalize.
        """,
    ).tag(config=True)

    def __init__(self, **kwargs):
        if pamela is None:
            raise _pamela_error from None
        super().__init__(**kwargs)

    @run_on_executor
    def is_admin(self, handler, authentication):
        """PAM admin status checker. Returns Bool to indicate user admin status."""
        # Checks upper level function (admin_users)
        admin_status = super().is_admin(handler, authentication)
        username = authentication['name']

        # If not yet listed as an admin, and admin_groups is on, use it authoritatively
        if not admin_status and self.admin_groups:
            try:
                # Most likely source of error here is a group name <-> gid mapping failure
                # This is most likely due to a typo in the configuration or in the case of LDAP/AD, a network
                # connectivity issue. Maybe a long one where the local caches have timed out, though PAM would
                # most likely would refuse to authenticate a remote user by that point.

                # It was decided that the best course of action on group resolution failure was to
                # fail to authenticate and raise instead of soft-failing and not changing admin status
                # (returning None instead of just the username) as this indicates some sort of system failure

                admin_group_gids = {self._getgrnam(x).gr_gid for x in self.admin_groups}
                user_group_gids = set(
                    self._getgrouplist(username, self._getpwnam(username).pw_gid)
                )
                admin_status = len(admin_group_gids & user_group_gids) != 0

            except Exception as e:
                if handler is not None:
                    self.log.error(
                        "PAM Admin Group Check failed (%s@%s): %s",
                        username,
                        handler.request.remote_ip,
                        e,
                    )
                else:
                    self.log.error("PAM Admin Group Check failed: %s", e)
                # re-raise to return a 500 to the user and indicate a problem. We failed, not them.
                raise

        return admin_status

    @run_on_executor
    def authenticate(self, handler, data):
        """Authenticate with PAM, and return the username if login is successful.

        Return None otherwise.
        """
        username = data['username']
        try:
            pamela.authenticate(
                username, data['password'], service=self.service, encoding=self.encoding
            )
        except pamela.PAMError as e:
            if handler is not None:
                self.log.warning(
                    "PAM Authentication failed (%s@%s): %s",
                    username,
                    handler.request.remote_ip,
                    e,
                )
            else:
                self.log.warning("PAM Authentication failed: %s", e)
            return None

        if self.check_account:
            try:
                pamela.check_account(
                    username, service=self.service, encoding=self.encoding
                )
            except pamela.PAMError as e:
                if handler is not None:
                    self.log.warning(
                        "PAM Account Check failed (%s@%s): %s",
                        username,
                        handler.request.remote_ip,
                        e,
                    )
                else:
                    self.log.warning("PAM Account Check failed: %s", e)
                return None

        return username

    @run_on_executor
    def pre_spawn_start(self, user, spawner):
        """Open PAM session for user if so configured"""
        if not self.open_sessions:
            return
        try:
            pamela.open_session(user.name, service=self.service, encoding=self.encoding)
        except pamela.PAMError as e:
            self.log.warning("Failed to open PAM session for %s: %s", user.name, e)
            self.log.warning("Disabling PAM sessions from now on.")
            self.open_sessions = False

    @run_on_executor
    def post_spawn_stop(self, user, spawner):
        """Close PAM session for user if we were configured to opened one"""
        if not self.open_sessions:
            return
        try:
            pamela.close_session(
                user.name, service=self.service, encoding=self.encoding
            )
        except pamela.PAMError as e:
            self.log.warning("Failed to close PAM session for %s: %s", user.name, e)
            self.log.warning("Disabling PAM sessions from now on.")
            self.open_sessions = False

    def normalize_username(self, username):
        """Round-trip the username to normalize it with PAM

        PAM can accept multiple usernames as the same user, normalize them."""
        if self.pam_normalize_username:
            import pwd

            uid = pwd.getpwnam(username).pw_uid
            username = pwd.getpwuid(uid).pw_name
            username = self.username_map.get(username, username)
            return username
        else:
            return super().normalize_username(username)


for _old_name, _new_name, _version in [
    ("check_group_whitelist", "check_group_allowed", "1.2"),
]:
    setattr(
        LocalAuthenticator,
        _old_name,
        _deprecated_method(_old_name, _new_name, _version),
    )


class DummyAuthenticator(Authenticator):
    """Dummy Authenticator for testing

    By default, any username + password is allowed
    If a non-empty password is set, any username will be allowed
    if it logs in with that password.

    .. versionadded:: 1.0
    """

    password = Unicode(
        config=True,
        help="""
        Set a global password for all users wanting to log in.

        This allows users with any username to log in with the same static password.
        """,
    )

    async def authenticate(self, handler, data):
        """Checks against a global password if it's been set. If not, allow any user/pass combo"""
        if self.password:
            if data['password'] == self.password:
                return data['username']
            return None
        return data['username']
