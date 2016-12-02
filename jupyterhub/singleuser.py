#!/usr/bin/env python
"""Extend regular notebook server to be aware of multiuser things."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

import os

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


class JupyterHubLoginHandler(LoginHandler):
    """LoginHandler that hooks up Hub authentication"""
    @staticmethod
    def login_available(settings):
        return True

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
    'user' : 'SingleUserNotebookApp.user',
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

    user = CUnicode(config=True)
    def _user_changed(self, name, old, new):
        self.log.name = new
    hub_prefix = Unicode().tag(config=True)
    hub_host = Unicode().tag(config=True)
    hub_api_url = Unicode().tag(config=True)
    aliases = aliases
    flags = flags
    
    # disble some single-user configurables
    token = ''
    open_browser = False
    trust_xheaders = True
    login_handler_class = JupyterHubLoginHandler
    logout_handler_class = JupyterHubLogoutHandler
    port_retries = 0 # disable port-retries, since the Spawner will tell us what port to use

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
        if not os.environ.get('JPY_API_TOKEN'):
            self.exit("JPY_API_TOKEN env is required to run jupyterhub-singleuser. Did you launch it manually?")
        self.hub_auth = HubAuth(
            parent=self,
            api_token=os.environ.pop('JPY_API_TOKEN'),
            api_url=self.hub_api_url,
        )

    def init_webapp(self):
        # load the hub related settings into the tornado settings dict
        self.init_hub_auth()
        s = self.tornado_settings
        s['user'] = self.user
        s['hub_prefix'] = self.hub_prefix
        s['hub_host'] = self.hub_host
        s['hub_auth'] = self.hub_auth
        s['login_url'] = self.hub_host + self.hub_prefix
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
