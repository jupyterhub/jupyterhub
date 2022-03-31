"""JupyterHub single-user server entrypoints

Contains default notebook-app subclass and mixins
"""
from .app import SingleUserNotebookApp, main
from .mixins import HubAuthenticatedHandler, make_singleuser_app

# backward-compatibility
JupyterHubLoginHandler = SingleUserNotebookApp.login_handler_class
JupyterHubLogoutHandler = SingleUserNotebookApp.logout_handler_class
OAuthCallbackHandler = SingleUserNotebookApp.oauth_callback_handler_class
