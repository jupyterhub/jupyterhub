import json
import os
from datetime import datetime, timezone

from nativeauthenticator import NativeAuthenticator
from nativeauthenticator.handlers import SignUpHandler

from jupyterhub.handlers import BaseHandler

base_dir = os.path.dirname(os.path.abspath(__file__))

PUBLIC_URL = 'https://104.248.22.193.sslip.io'
# Secrets are injected from secrets.env (sourced by start-hub.sh) and are NOT
# committed to git. See secrets.env.example for the expected variables.
PROMETHEUS_TOKEN = os.environ.get('SAIEP_PROMETHEUS_TOKEN')
MONITORING_TOKEN = os.environ.get('SAIEP_MONITORING_TOKEN')
if not PROMETHEUS_TOKEN or not MONITORING_TOKEN:
    raise RuntimeError(
        "Missing SAIEP_PROMETHEUS_TOKEN/SAIEP_MONITORING_TOKEN (see secrets.env.example)"
    )
c.JupyterHub.template_paths = [os.path.join(base_dir, 'templates')]

# Bind to the Docker bridge gateway only — reachable by the Caddy HTTPS proxy
# (and the host), NOT directly from the public internet.
c.JupyterHub.bind_url = 'http://172.17.0.1:8000'

# Caddy terminates TLS and forwards X-Forwarded-Proto=https so the Hub
# issues secure cookies and correct redirects.
c.JupyterHub.trusted_downstream_ips = ['172.17.0.0/16', '127.0.0.1']

# --- Authentication: demande d'inscription + activation par l'admin -------
# Workflow demanded by LITAN: users request an account at /hub/signup with
# their ESTIN email; admin LITAN verifies identity at /hub/authorize and
# activates the account. Only then can the user log in.
#
# At signup we also collect the researcher's project context (requested by
# Dalil HADJOUT): research theme, project type (NLP / Vision / Time series /
# other), lab and supervisor. These are persisted to researcher-profiles.jsonl
# so LITAN can review them at activation time and so they feed later analytics.
RESEARCHER_PROFILES_LOG = os.path.join(base_dir, 'researcher-profiles.jsonl')


class SAIEPSignUpHandler(SignUpHandler):
    """Captures the extra research fields from the signup form before
    delegating to NativeAuthenticator's normal account-creation logic."""

    async def post(self):
        username = self.get_body_argument('username', '', strip=True)
        # Only record genuinely new signup requests (skip retries on an
        # existing username, e.g. validation errors).
        if username and not self.authenticator.user_exists(username):
            profile = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'username': username,
                'email': self.get_body_argument('email', '', strip=True),
                'project_theme': self.get_body_argument(
                    'project_theme', '', strip=True
                )[:500],
                'project_type': self.get_body_argument('project_type', '', strip=True),
                'lab': self.get_body_argument('lab', '', strip=True)[:200],
                'supervisor': self.get_body_argument('supervisor', '', strip=True)[
                    :200
                ],
                'description': self.get_body_argument(
                    'research_description', '', strip=True
                )[:2000],
            }
            try:
                with open(RESEARCHER_PROFILES_LOG, 'a') as f:
                    f.write(json.dumps(profile, ensure_ascii=False) + '\n')
            except OSError:
                self.log.warning(
                    'Could not persist researcher profile for %s', username
                )
        await super().post()


class SAIEPAuthenticator(NativeAuthenticator):
    """NativeAuthenticator that swaps in our research-aware signup handler."""

    def get_handlers(self, app):
        handlers = super().get_handlers(app)
        return [
            (path, SAIEPSignUpHandler if path == r'/signup' else handler)
            for path, handler in handlers
        ]


c.JupyterHub.authenticator_class = SAIEPAuthenticator
c.Authenticator.admin_users = {'r4y4n3', 'litan'}
# NativeAuthenticator enforces account activation itself (is_authorized) in
# authenticate(); JupyterHub >= 5 additionally requires an explicit allow
# rule, so allow_all here does NOT bypass the admin-approval workflow.
c.Authenticator.allow_all = True
c.NativeAuthenticator.open_signup = False  # activation by admin required
c.NativeAuthenticator.ask_email_on_signup = True  # ESTIN email for identity check
c.NativeAuthenticator.minimum_password_length = 8
c.NativeAuthenticator.allowed_failed_logins = 5
c.NativeAuthenticator.seconds_before_next_try = 600


# --- Page d'accueil publique (landing) -------------------------------------
# Page de présentation SAIEP affichée aux visiteurs (intégrée depuis le
# travail de l'équipe). Servie publiquement à /hub/landing.
class LandingHandler(BaseHandler):
    async def get(self):
        landing = os.path.join(base_dir, 'static', 'landing', 'index.html')
        with open(landing, encoding='utf-8') as f:
            self.finish(f.read())


c.JupyterHub.extra_handlers = [
    (r'/landing', LandingHandler),
]


# --- Redirection par rôle après connexion ----------------------------------
# Les visiteurs non connectés voient la page d'accueil ; après connexion,
# chaque rôle arrive directement sur son espace : le super admin sur l'IHM
# de configuration, l'admin LITAN sur l'activation des comptes, les
# utilisateurs sur leur serveur (formulaire de dimensionnement).
def default_url(handler):
    user = handler.current_user
    if user is None:
        return '/hub/landing'
    if user.name == 'r4y4n3':
        return '/hub/admin'
    if user.name == 'litan':
        return '/hub/authorize'
    return '/hub/spawn'


c.JupyterHub.default_url = default_url

# --- Spawner + formulaire de dimensionnement -------------------------------
# Before each server starts, the user fills a sizing form (CPU/RAM/duration/
# usage). Requests are persisted to spawn-requests.jsonl: this is the dataset
# the future AI sizing model will train on.
SPAWN_REQUESTS_LOG = os.path.join(base_dir, 'spawn-requests.jsonl')

SIZING_FORM = """
<div class="saiep-sizing-form">
  <p>Veuillez dimensionner votre espace d'exécution :</p>
  <label for="cpu">Processeur (vCPU) :</label>
  <select name="cpu" class="form-control">
    <option value="0.5">0.5 vCPU</option>
    <option value="1" selected>1 vCPU</option>
    <option value="2">2 vCPU</option>
  </select>
  <br/>
  <label for="memory">Mémoire (RAM) :</label>
  <select name="memory" class="form-control">
    <option value="512M">512 Mo</option>
    <option value="1G" selected>1 Go</option>
    <option value="2G">2 Go</option>
    <option value="4G">4 Go</option>
  </select>
  <br/>
  <label for="duration">Durée estimée d'utilisation :</label>
  <select name="duration" class="form-control">
    <option value="1h" selected>1 heure</option>
    <option value="4h">4 heures</option>
    <option value="1d">1 journée</option>
    <option value="1w">1 semaine</option>
  </select>
  <br/>
  <label for="usage">Description de l'usage (librairies, type de calcul, dataset...) :</label>
  <textarea name="usage" class="form-control" rows="3"
    placeholder="Ex: entraînement d'un modèle scikit-learn sur un CSV de 200 Mo"></textarea>
</div>
"""


def options_from_form(formdata):
    options = {
        'cpu': formdata.get('cpu', ['1'])[0],
        'memory': formdata.get('memory', ['1G'])[0],
        'duration': formdata.get('duration', ['1h'])[0],
        'usage': formdata.get('usage', [''])[0][:2000],
    }
    return options


def pre_spawn_hook(spawner):
    """Record every sizing request (training data for the future AI model)
    and pass the requested limits to the user's environment."""
    options = spawner.user_options or {}
    record = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'user': spawner.user.name,
        'options': options,
    }
    try:
        with open(SPAWN_REQUESTS_LOG, 'a') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    except OSError:
        spawner.log.warning('Could not persist spawn sizing request')
    spawner.environment.update(
        {
            'SAIEP_CPU_REQUEST': str(options.get('cpu', '')),
            'SAIEP_MEM_REQUEST': str(options.get('memory', '')),
        }
    )


c.JupyterHub.spawner_class = 'simple'
c.Spawner.cmd = [os.path.join(base_dir, 'venv/bin/jupyterhub-singleuser')]
c.Spawner.default_url = '/lab'
c.Spawner.options_form = SIZING_FORM
c.Spawner.options_from_form = options_from_form
c.Spawner.pre_spawn_hook = pre_spawn_hook

# --- Monitoring intégré DANS JupyterHub (demande de Dalil) -----------------
# Grafana n'est plus une application indépendante : il est servi par le hub
# sous /services/monitoring et utilise JupyterHub comme fournisseur d'identité
# (Single Sign-On). On se connecte une seule fois à JupyterHub ; Grafana
# reconnaît automatiquement l'utilisateur et son rôle (Admin pour r4y4n3 /
# litan, Viewer pour les autres). Prometheus reste interne (non exposé).
c.JupyterHub.services = [
    {
        # Service token used by Prometheus to scrape /hub/metrics.
        'name': 'prometheus',
        'api_token': PROMETHEUS_TOKEN,
    },
    {
        # Grafana, proxied by the hub at /services/monitoring with hub OAuth.
        'name': 'monitoring',
        'url': 'http://127.0.0.1:3000',
        'api_token': MONITORING_TOKEN,
        'oauth_redirect_uri': PUBLIC_URL + '/services/monitoring/login/generic_oauth',
        'oauth_no_confirm': True,
    },
]
c.JupyterHub.load_roles = [
    {
        'name': 'metrics-scraper',
        'scopes': ['read:metrics'],
        'services': ['prometheus'],
    },
    {
        # Only the admins (LITAN + super admin) may open the monitoring space.
        'name': 'monitoring-access',
        'scopes': ['access:services!service=monitoring'],
        'users': ['r4y4n3', 'litan'],
    },
]
