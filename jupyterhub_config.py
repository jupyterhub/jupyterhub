c.JupyterHub.template_paths = ['/home/celia/SAIEP/ESTIN-SAIEP/templates']
c.Authenticator.allow_all = True
c.Authenticator.admin_users = {'celia'}
c.Spawner.cmd = ['/home/celia/SAIEP/ESTIN-SAIEP/venv/bin/jupyterhub-singleuser']
# ─── Landing Page ───────────────────────────────────────────
import os
from jupyterhub.handlers import BaseHandler

class LandingHandler(BaseHandler):
    async def get(self):
        landing = os.path.join(
            os.path.dirname(__file__),
            'static', 'landing', 'index.html'
        )
        with open(landing, 'r', encoding='utf-8') as f:
            self.finish(f.read())

c.JupyterHub.extra_handlers = [
    (r'/landing', LandingHandler),
]

c.JupyterHub.default_url = '/landing'
# ────────────────────────────────────────────────────────────
