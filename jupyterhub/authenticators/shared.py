from secrets import compare_digest

from traitlets import Unicode, validate

from ..auth import Authenticator


class SharedPasswordAuthenticator(Authenticator):
    """
    Authenticator with static shared passwords.

    For use in short-term deployments with negligible security concerns.

    Enable with::

        c.JupyterHub.authenticator_class = "shared-password"

    .. warning::
        This is an insecure Authenticator only appropriate for short-term
        deployments with no requirement to protect users from each other.

        - The password is stored in plain text at rest in config
        - Anyone with the password can login as **any user**
        - All users are able to login as all other (non-admin) users with the same password
    """

    _USER_PASSWORD_MIN_LENGTH = 8
    _ADMIN_PASSWORD_MIN_LENGTH = 32

    user_password = Unicode(
        None,
        allow_none=True,
        config=True,
        help=f"""
        Set a global password for all *non admin* users wanting to log in.

        Must be {_USER_PASSWORD_MIN_LENGTH} characters or longer.

        If not set, regular users cannot login.

        If `allow_all` is True, anybody can register unlimited new users with any username by logging in with this password.
        Users may be allowed by name by specifying `allowed_users`.

        Any user will also be able to login as **any other non-admin user** with this password.

        If `admin_users` is set, those users *must* use `admin_password` to log in.
        """,
    )

    admin_password = Unicode(
        None,
        allow_none=True,
        config=True,
        help=f"""
        Set a global password that grants *admin* privileges to users logging in with this password.
        Only usernames declared in `admin_users` may login with this password.

        Must meet the following requirements:

        - Be {_ADMIN_PASSWORD_MIN_LENGTH} characters or longer
        - Not be the same as `user_password`

        If not set, admin users cannot login.
        """,
    )

    @validate("admin_password")
    def _validate_admin_password(self, proposal):
        new = proposal.value
        trait_name = f"{self.__class__.__name__}.{proposal.trait.name}"

        if not new:
            # no admin password; do nothing
            return None
        if len(new) < self._ADMIN_PASSWORD_MIN_LENGTH:
            raise ValueError(
                f"{trait_name} must be at least {self._ADMIN_PASSWORD_MIN_LENGTH} characters, not {len(new)}."
            )
        if self.user_password == new:
            # Checked here and in validating password, to ensure we don't miss issues due to ordering
            raise ValueError(
                f"{self.__class__.__name__}.user_password and {trait_name} cannot be the same"
            )
        return new

    @validate("user_password")
    def _validate_password(self, proposal):
        new = proposal.value
        trait_name = f"{self.__class__.__name__}.{proposal.trait.name}"

        if not new:
            # no user password; do nothing
            return None
        if len(new) < self._USER_PASSWORD_MIN_LENGTH:
            raise ValueError(
                f"{trait_name} must be at least {self._USER_PASSWORD_MIN_LENGTH} characters long, got {len(new)} characters"
            )
        if self.admin_password == new:
            # Checked here and in validating password, to ensure we don't miss issues due to ordering
            raise ValueError(
                f"{trait_name} and {self.__class__.__name__}.admin_password cannot be the same"
            )
        return new

    def check_allow_config(self):
        """Validate and warn about any suspicious allow config"""
        super().check_allow_config()
        clsname = self.__class__.__name__
        if self.admin_password and not self.admin_users:
            self.log.warning(
                f"{clsname}.admin_password set, but {clsname}.admin_users is not."
                " No admin users will be able to login."
                f" Add usernames to {clsname}.admin_users to grant users admin permissions."
            )
        if self.admin_users and not self.admin_password:
            self.log.warning(
                f"{clsname}.admin_users set, but {clsname}.admin_password is not."
                " No admin users will be able to login."
                f" Set {clsname}.admin_password to allow admins to login."
            )
        if not self.user_password:
            if not self.admin_password:
                # log as an error, but don't raise, because disabling all login is valid
                self.log.error(
                    f"Neither {clsname}.admin_password nor {clsname}.user_password is set."
                    " Nobody will be able to login!"
                )
            else:
                self.log.warning(
                    f"{clsname}.user_password not set."
                    " No non-admin users will be able to login."
                )

    async def authenticate(self, handler, data):
        """Checks against shared password"""
        if data["username"] in self.admin_users:
            # Admin user
            if self.admin_password and compare_digest(
                data["password"], self.admin_password
            ):
                return {"name": data["username"], "admin": True}
        else:
            if self.user_password and compare_digest(
                data["password"], self.user_password
            ):
                # Anyone logging in with the standard password is *never* admin
                return {"name": data["username"], "admin": False}

        return None
