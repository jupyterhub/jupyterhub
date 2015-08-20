"""Basic html-rendering handlers."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from tornado import web

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
        running = users.filter(orm.User.server != None)
        
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
]
