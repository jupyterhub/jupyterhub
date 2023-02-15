import os

from jupyterhub.singleuser.extension import JupyterHubAuthorizer


class GranularJupyterHubAuthorizer(JupyterHubAuthorizer):
    """Authorizer that looks for permissions in JupyterHub scopes"""

    def is_authorized(self, handler, user, action, resource):
        # authorize if any of these permissions are present
        # filters check for access to this specific user or server
        # group filters aren't available!
        filters = [
            f"!user={os.environ['JUPYTERHUB_USER']}",
            f"!server={os.environ['JUPYTERHUB_USER']}/{os.environ['JUPYTERHUB_SERVER_NAME']}",
        ]
        required_scopes = set()
        for f in filters:
            required_scopes.update(
                {
                    f"custom:jupyter_server:{action}:{resource}{f}",
                    f"custom:jupyter_server:{action}:*{f}",
                }
            )

        have_scopes = self.hub_auth.check_scopes(required_scopes, user.hub_user)
        self.log.debug(
            f"{user.username} has permissions {have_scopes} required to {action} on {resource}"
        )
        return bool(have_scopes)


c = get_config()  # noqa


c.ServerApp.authorizer_class = GranularJupyterHubAuthorizer
