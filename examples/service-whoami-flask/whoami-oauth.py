#!/usr/bin/env python3
"""
whoami service authentication with the Hub
"""
import json
import os
from functools import wraps

from flask import Flask
from flask import make_response
from flask import redirect
from flask import request
from flask import Response

from jupyterhub.services.auth import HubOAuth


prefix = os.environ.get('JUPYTERHUB_SERVICE_PREFIX', '/')

auth = HubOAuth(api_token=os.environ['JUPYTERHUB_API_TOKEN'], cache_max_age=60)

app = Flask(__name__)


def authenticated(f):
    """Decorator for authenticating with the Hub via OAuth"""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get(auth.cookie_name)
        if token:
            user = auth.user_for_token(token)
        else:
            user = None
        if user:
            return f(user, *args, **kwargs)
        else:
            # redirect to login url on failed auth
            state = auth.generate_state(next_url=request.path)
            response = make_response(redirect(auth.login_url + '&state=%s' % state))
            response.set_cookie(auth.state_cookie_name, state)
            return response

    return decorated


@app.route(prefix)
@authenticated
def whoami(user):
    return Response(
        json.dumps(user, indent=1, sort_keys=True), mimetype='application/json'
    )


@app.route(prefix + 'oauth_callback')
def oauth_callback():
    code = request.args.get('code', None)
    if code is None:
        return 403

    # validate state field
    arg_state = request.args.get('state', None)
    cookie_state = request.cookies.get(auth.state_cookie_name)
    if arg_state is None or arg_state != cookie_state:
        # state doesn't match
        return 403

    token = auth.token_for_code(code)
    next_url = auth.get_next_url(cookie_state) or prefix
    response = make_response(redirect(next_url))
    response.set_cookie(auth.cookie_name, token)
    return response
