from traitlets import Unicode, default, validate

from ..auth import Authenticator


class SharedPasswordAuthenticator(Authenticator):
    """
    Authenticator with static shared passwords.
    """

    @default("allow_all")
    def _allow_all_default(self):
        if self.allowed_users:
            return False
        else:
            # allow all by default
            return True

    global_password = Unicode(
        None,
        allow_none=True,  # Allow None here, so we can provide a better error message in our validation
        config=True,
        help="""
        Set a global password for all *non admin* users wanting to log in.

        Must be 8 characters or longer.

        If `allowed_users` is not set, any user with any username can login with this password.
        If `allowed_users` is set, only the set of usernames present in `allowed_users` can log in-
        although they all use the same password.

        If `admin_users` is set, those users *must* use `admin_password` to log in.
        """,
    )

    admin_password = Unicode(
        None,
        allow_none=True,
        config=True,
        help="""
        Set a global password that grants *admin* privileges to users logging in with this password.

        Must meet the following requirements:
        - Be 32 characters or longer
        - password for regular users (global_password) must also be set
        - Not be the same as the password

        Admin access to the hub is disabled if this is not set.
        """,
    )

    @validate("admin_password")
    def _validate_admin_password(self, proposal):
        new = proposal.value
        if new is None:
            # Don't do anything if we're None
            return None
        if len(new) < 32:
            raise ValueError(
                f"{self.__class__.__name__}.admin_password must be at least 32 characters"
            )
        if not self.global_password:
            # Checked here and in validating password, to ensure we don't miss issues due to ordering
            raise ValueError(
                f"{self.__class__.__name__}.global_password must be set if admin_password is set"
            )
        if self.global_password == new:
            # Checked here and in validating password, to ensure we don't miss issues due to ordering
            raise ValueError(
                f"{self.__class__.__name__}.global_password and {self.__class__.__name__}.admin_password can not be the same"
            )
        return new

    @validate("password")
    def _validate_password(self, proposal):
        new = proposal.value

        if new is None:
            raise ValueError(
                f"{self.__class__.__name__}.global_password must be set to use {self.__class__.__name__}"
            )
        if new and len(new) < 8:
            raise ValueError(
                f"{self.__class__.__name__}.global_password must be at least 8 characters long"
            )

        if self.admin_password and not new:
            # Checked here and in validating admin_password, to ensure we don't miss issues due to ordering
            raise ValueError(
                f"{self.__class__.__name__}.global_password must be set if admin_password is set"
            )

        if not new:
            # If unset, let it be
            return new

        if self.admin_password == new:
            # Checked here and in validating password, to ensure we don't miss issues due to ordering
            raise ValueError(
                f"{self.__class__.__name__}.global_password and {self.__class__.__name__}.admin_password can not be the same"
            )

        return new

    async def authenticate(self, handler, data):
        """Checks against a global password if it's been set. If not, allow any user/pass combo"""
        if data['username'] in self.admin_users:
            # Admin user
            if data['password'] == self.admin_password:
                return {"name": data["username"], "admin": True}
        else:
            # Regular user
            if data['password'] == self.global_password:
                # Anyone logging in with the standard password is *never* admin
                return {"name": data['username'], "admin": False}

        return None
