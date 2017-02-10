#!/usr/bin/env python
"""Extend regular notebook server to be aware of multiuser things."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import os
from urllib.parse import urlparse

from jinja2 import ChoiceLoader, FunctionLoader

from tornado import ioloop
from textwrap import dedent

try:
    import notebook
except ImportError:
    raise ImportError("JupyterHub single-user server requires notebook >= 4.0")

from traitlets import (
    Bool,
    Unicode,
    CUnicode,
    default,
    observe,
    validate,
    TraitError,
)

from notebook.notebookapp import (
    NotebookApp,
    aliases as notebook_aliases,
    flags as notebook_flags,
)
from notebook.auth.login import LoginHandler
from notebook.auth.logout import LogoutHandler

from jupyterhub import __version__
from .services.auth import HubAuth, HubAuthenticated
from .utils import url_path_join


# Authenticate requests with the Hub


class HubAuthenticatedHandler(HubAuthenticated):
    """Class we are going to patch-in for authentication with the Hub"""
    @property
    def hub_auth(self):
        return self.settings['hub_auth']

    @property
    def hub_users(self):
        return { self.settings['user'] }

    @property
    def hub_groups(self):
        if self.settings['group']:
            return { self.settings['group'] }
        return set()


class JupyterHubLoginHandler(LoginHandler):
    """LoginHandler that hooks up Hub authentication"""
    @staticmethod
    def login_available(settings):
        return True

    @staticmethod
    def is_token_authenticated(handler):
        """Is the request token-authenticated?"""
        if getattr(handler, '_cached_hub_user', None) is None:
            # ensure get_user has been called, so we know if we're token-authenticated
            handler.get_current_user()
        return getattr(handler, '_token_authenticated', False)

    @staticmethod
    def get_user(handler):
        """alternative get_current_user to query the Hub"""
        # patch in HubAuthenticated class for querying the Hub for cookie authentication
        name = 'NowHubAuthenticated'
        if handler.__class__.__name__ != name:
            handler.__class__ = type(name, (HubAuthenticatedHandler, handler.__class__), {})
        return handler.get_current_user()


class JupyterHubLogoutHandler(LogoutHandler):
    def get(self):
        self.redirect(
            self.settings['hub_host'] +
            url_path_join(self.settings['hub_prefix'], 'logout'))


# register new hub related command-line aliases
aliases = dict(notebook_aliases)
aliases.update({
    'user': 'SingleUserNotebookApp.user',
    'group': 'SingleUserNotebookApp.group',
    'cookie-name': 'HubAuth.cookie_name',
    'hub-prefix': 'SingleUserNotebookApp.hub_prefix',
    'hub-host': 'SingleUserNotebookApp.hub_host',
    'hub-api-url': 'SingleUserNotebookApp.hub_api_url',
    'base-url': 'SingleUserNotebookApp.base_url',
})
flags = dict(notebook_flags)
flags.update({
    'disable-user-config': ({
        'SingleUserNotebookApp': {
            'disable_user_config': True
        }
    }, "Disable user-controlled configuration of the notebook server.")
})

page_template = """
{% extends "templates/page.html" %}

{% block header_buttons %}
{{super()}}

<a href='{{hub_control_panel_url}}'
 class='btn btn-default btn-sm navbar-btn pull-right'
 style='margin-right: 4px; margin-left: 2px;'
>
Control Panel</a>
{% endblock %}
{% block logo %}
<img src='{{logo_url}}' alt='Jupyter Notebook'/>
{% endblock logo %}
"""


def _exclude_home(path_list):
    """Filter out any entries in a path list that are in my home directory.

    Used to disable per-user configuration.
    """
    home = os.path.expanduser('~')
    for p in path_list:
        if not p.startswith(home):
            yield p


class SingleUserNotebookApp(NotebookApp):
    """A Subclass of the regular NotebookApp that is aware of the parent multiuser context."""
    description = dedent("""
    Single-user server for JupyterHub. Extends the Jupyter Notebook server.

    Meant to be invoked by JupyterHub Spawners, and not directly.
    """)

    examples = ""
    subcommands = {}
    version = __version__
    classes = NotebookApp.classes + [HubAuth]

    user = CUnicode().tag(config=True)
    group = CUnicode().tag(config=True)

    @observe('user')
    def _user_changed(self, change):
        self.log.name = change.new

    hub_host = Unicode().tag(config=True)

    hub_prefix = Unicode('/hub/').tag(config=True)

    @default('hub_prefix')
    def _hub_prefix_default(self):
        base_url = os.environ.get('JUPYTERHUB_BASE_URL') or '/'
        return base_url + 'hub/'

    hub_api_url = Unicode().tag(config=True)

    @default('hub_api_url')
    def _hub_api_url_default(self):
        return os.environ.get('JUPYTERHUB_API_URL') or 'http://127.0.0.1:8081/hub/api'

    # defaults for some configurables that may come from service env variables:
    @default('base_url')
    def _base_url_default(self):
        return os.environ.get('JUPYTERHUB_SERVICE_PREFIX') or '/'

    @default('cookie_name')
    def _cookie_name_default(self):
        if os.environ.get('JUPYTERHUB_SERVICE_NAME'):
            # if I'm a service, use the services cookie name
            return 'jupyterhub-services'

    @default('port')
    def _port_default(self):
        if os.environ.get('JUPYTERHUB_SERVICE_URL'):
            url = urlparse(os.environ['JUPYTERHUB_SERVICE_URL'])
            return url.port

    @default('ip')
    def _ip_default(self):
        if os.environ.get('JUPYTERHUB_SERVICE_URL'):
            url = urlparse(os.environ['JUPYTERHUB_SERVICE_URL'])
            return url.hostname

    aliases = aliases
    flags = flags

    # disble some single-user configurables
    token = ''
    open_browser = False
    trust_xheaders = True
    login_handler_class = JupyterHubLoginHandler
    logout_handler_class = JupyterHubLogoutHandler
    port_retries = 0  # disable port-retries, since the Spawner will tell us what port to use

    disable_user_config = Bool(False,
        help="""Disable user configuration of single-user server.

        Prevents user-writable files that normally configure the single-user server
        from being loaded, ensuring admins have full control of configuration.
        """
    ).tag(config=True)

    @validate('notebook_dir')
    def _notebook_dir_validate(self, proposal):
        value = os.path.expanduser(proposal['value'])
        # Strip any trailing slashes
        # *except* if it's root
        _, path = os.path.splitdrive(value)
        if path == os.sep:
            return value
        value = value.rstrip(os.sep)
        if not os.path.isabs(value):
            # If we receive a non-absolute path, make it absolute.
            value = os.path.abspath(value)
        if not os.path.isdir(value):
            raise TraitError("No such notebook dir: %r" % value)
        return value

    @default('log_datefmt')
    def _log_datefmt_default(self):
        """Exclude date from default date format"""
        return "%Y-%m-%d %H:%M:%S"

    @default('log_format')
    def _log_format_default(self):
        """override default log format to include time"""
        return "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s %(module)s:%(lineno)d]%(end_color)s %(message)s"

    def _confirm_exit(self):
        # disable the exit confirmation for background notebook processes
        ioloop.IOLoop.instance().stop()

    def migrate_config(self):
        if self.disable_user_config:
            # disable config-migration when user config is disabled
            return
        else:
            super(SingleUserNotebookApp, self).migrate_config()

    @property
    def config_file_paths(self):
        path = super(SingleUserNotebookApp, self).config_file_paths

        if self.disable_user_config:
            # filter out user-writable config dirs if user config is disabled
            path = list(_exclude_home(path))
        return path

    @property
    def nbextensions_path(self):
        path = super(SingleUserNotebookApp, self).nbextensions_path

        if self.disable_user_config:
            path = list(_exclude_home(path))
        return path

    @validate('static_custom_path')
    def _validate_static_custom_path(self, proposal):
        path = proposal['value']
        if self.disable_user_config:
            path = list(_exclude_home(path))
        return path

    def start(self):
        super(SingleUserNotebookApp, self).start()

    def init_hub_auth(self):
        api_token = None
        if os.getenv('JPY_API_TOKEN'):
            # Deprecated env variable (as of 0.7.2)
            api_token = os.environ['JPY_API_TOKEN']
        if os.getenv('JUPYTERHUB_API_TOKEN'):
            api_token = os.environ['JUPYTERHUB_API_TOKEN']

        if not api_token:
            self.exit("JUPYTERHUB_API_TOKEN env is required to run jupyterhub-singleuser. Did you launch it manually?")
        self.hub_auth = HubAuth(
            parent=self,
            api_token=api_token,
            api_url=self.hub_api_url,
        )

    def init_webapp(self):
        # load the hub related settings into the tornado settings dict
        self.init_hub_auth()
        s = self.tornado_settings
        s['user'] = self.user
        s['group'] = self.group
        s['hub_prefix'] = self.hub_prefix
        s['hub_host'] = self.hub_host
        s['hub_auth'] = self.hub_auth
        self.hub_auth.login_url = self.hub_host + self.hub_prefix
        s['csp_report_uri'] = self.hub_host + url_path_join(self.hub_prefix, 'security/csp-report')
        super(SingleUserNotebookApp, self).init_webapp()
        self.patch_templates()

    def patch_templates(self):
        """Patch page templates to add Hub-related buttons"""

        self.jinja_template_vars['logo_url'] = self.hub_host + url_path_join(self.hub_prefix, 'logo')
        self.jinja_template_vars['hub_host'] = self.hub_host
        self.jinja_template_vars['hub_prefix'] = self.hub_prefix
        env = self.web_app.settings['jinja2_env']

        env.globals['hub_control_panel_url'] = \
            self.hub_host + url_path_join(self.hub_prefix, 'home')

        # patch jinja env loading to modify page template
        def get_page(name):
            if name == 'page.html':
                return page_template

        orig_loader = env.loader
        env.loader = ChoiceLoader([
            FunctionLoader(get_page),
            orig_loader,
        ])


def main(argv=None):
    return SingleUserNotebookApp.launch_instance(argv)


if __name__ == "__main__":
    main()
