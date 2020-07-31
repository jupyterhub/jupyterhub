"""JupyterHub single-user server entrypoints

Contains default notebook-app subclass and mixins
"""
from .app import main
from .app import SingleUserNotebookApp
from .mixins import HubAuthenticatedHandler
from .mixins import make_singleuser_app

# backward-compatibility
JupyterHubLoginHandler = SingleUserNotebookApp.login_handler_class
JupyterHubLogoutHandler = SingleUserNotebookApp.logout_handler_class
OAuthCallbackHandler = SingleUserNotebookApp.oauth_callback_handler_class
