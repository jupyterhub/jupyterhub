"""Basic html-rendering handlers."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from tornado import web, gen

from .. import orm
from ..utils import admin_only, url_path_join
from .base import BaseHandler
from .login import LoginHandler


class RootHandler(BaseHandler):
    """Render the Hub root page.
    
    If logged in, redirects to:
    
    - single-user server if running
    - hub home, otherwise
    
    Otherwise, renders login page.
    """
    def get(self):
        user = self.get_current_user()
        if user:
            if user.running:
                url = user.server.base_url
                self.log.debug("User is running: %s", url)
            else:
                url = url_path_join(self.hub.server.base_url, 'home')
                self.log.debug("User is not running: %s", url)
            self.redirect(url)
            return
        url = url_path_join(self.hub.server.base_url, 'login')
        self.redirect(url)


class HomeHandler(BaseHandler):
    """Render the user's home page."""

    @web.authenticated
    def get(self):
        html = self.render_template('home.html',
            user=self.get_current_user(),
        )
        self.finish(html)


class SpawnHandler(BaseHandler):
    """Handle spawning of single-user servers via form.
    
    GET renders the form, POST handles form submission.
    
    Only enabled when Spawner.options_form is defined.
    """
    def _render_form(self, message=''):
        user = self.get_current_user()
        return self.render_template('spawn.html',
            user=user,
            spawner_options_form=user.spawner.options_form,
            error_message=message,
        )

    @web.authenticated
    def get(self):
        """GET renders form for spawning with user-specified options"""
        user = self.get_current_user()
        if user.running:
            url = user.server.base_url
            self.log.debug("User is running: %s", url)
            self.redirect(url)
            return
        if user.spawner.options_form:
            self.finish(self._render_form())
        else:
            # not running, no form. Trigger spawn.
            url = url_path_join(self.base_url, 'user', user.name)
            self.redirect(url)
    
    @web.authenticated
    @gen.coroutine
    def post(self):
        """POST spawns with user-specified options"""
        user = self.get_current_user()
        if user.running:
            url = user.server.base_url
            self.log.warning("User is already running: %s", url)
            self.redirect(url)
            return
        form_options = {}
        for key, byte_list in self.request.body_arguments.items():
            form_options[key] = [ bs.decode('utf8') for bs in byte_list ]
        for key, byte_list in self.request.files.items():
            form_options["%s_file"%key] = byte_list
        try:
            options = user.spawner.options_from_form(form_options)
            yield self.spawn_single_user(user, options=options)
        except Exception as e:
            self.log.error("Failed to spawn single-user server with form", exc_info=True)
            self.finish(self._render_form(str(e)))
            return
        self.set_login_cookie(user)
        url = user.server.base_url
        self.redirect(url)

class AdminHandler(BaseHandler):
    """Render the admin page."""

    @admin_only
    def get(self):
        available = {'name', 'admin', 'running', 'last_activity'}
        default_sort = ['admin', 'name']
        mapping = {
            'running': '_server_id'
        }
        default_order = {
            'name': 'asc',
            'last_activity': 'desc',
            'admin': 'desc',
            'running': 'desc',
        }
        sorts = self.get_arguments('sort') or default_sort
        orders = self.get_arguments('order')
        
        for bad in set(sorts).difference(available):
            self.log.warn("ignoring invalid sort: %r", bad)
            sorts.remove(bad)
        for bad in set(orders).difference({'asc', 'desc'}):
            self.log.warn("ignoring invalid order: %r", bad)
            orders.remove(bad)
        
        # add default sort as secondary
        for s in default_sort:
            if s not in sorts:
                sorts.append(s)
        if len(orders) < len(sorts):
            for col in sorts[len(orders):]:
                orders.append(default_order[col])
        else:
            orders = orders[:len(sorts)]
        
        # this could be one incomprehensible nested list comprehension
        # get User columns
        cols = [ getattr(orm.User, mapping.get(c, c)) for c in sorts ]
        # get User.col.desc() order objects
        ordered = [ getattr(c, o)() for c, o in zip(cols, orders) ]
        
        users = self.db.query(orm.User).order_by(*ordered)
        users = [ self._user_from_orm(u) for u in users ]
        running = [ u for u in users if u.running ]
        
        html = self.render_template('admin.html',
            user=self.get_current_user(),
            admin_access=self.settings.get('admin_access', False),
            users=users,
            running=running,
            sort={s:o for s,o in zip(sorts, orders)},
        )
        self.finish(html)


default_handlers = [
    (r'/', RootHandler),
    (r'/home', HomeHandler),
    (r'/admin', AdminHandler),
    (r'/spawn', SpawnHandler),
]
