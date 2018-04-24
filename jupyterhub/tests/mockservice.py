"""Mock service for testing Service integration

A JupyterHub service running a basic HTTP server.

Used by the `mockservice` fixtures found in `conftest.py` file.

Handlers and their purpose include:

- EchoHandler: echoing proxied URLs back
- EnvHandler: retrieving service's environment variables
- APIHandler: testing service's API access to the Hub retrieval of `sys.argv`.
- WhoAmIHandler: returns name of user making a request (deprecated cookie login)
- OWhoAmIHandler: returns name of user making a request (OAuth login)
"""

import json
import pprint
import os
import sys
from urllib.parse import urlparse

import requests
from tornado import web, httpserver, ioloop

from jupyterhub.services.auth import HubAuthenticated, HubOAuthenticated, HubOAuthCallbackHandler


class EchoHandler(web.RequestHandler):
    """Reply to an HTTP request with the path of the request."""
    def get(self):
        self.write(self.request.path)


class EnvHandler(web.RequestHandler):
    """Reply to an HTTP request with the service's environment as JSON."""
    def get(self):
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(dict(os.environ)))


class APIHandler(web.RequestHandler):
    """Relay API requests to the Hub's API using the service's API token."""
    def get(self, path):
        api_token = os.environ['JUPYTERHUB_API_TOKEN']
        api_url = os.environ['JUPYTERHUB_API_URL']
        r = requests.get(api_url + path,
            headers={'Authorization': 'token %s' % api_token},
        )
        r.raise_for_status()
        self.set_header('Content-Type', 'application/json')
        self.write(r.text)


class WhoAmIHandler(HubAuthenticated, web.RequestHandler):
    """Reply with the name of the user who made the request.
    
    Uses "deprecated" cookie login
    """
    @web.authenticated
    def get(self):
        self.write(self.get_current_user())


class OWhoAmIHandler(HubOAuthenticated, web.RequestHandler):
    """Reply with the name of the user who made the request.
    
    Uses OAuth login flow
    """
    @web.authenticated
    def get(self):
        self.write(self.get_current_user())


def main():
    pprint.pprint(dict(os.environ), stream=sys.stderr)

    if os.getenv('JUPYTERHUB_SERVICE_URL'):
        url = urlparse(os.environ['JUPYTERHUB_SERVICE_URL'])
        app = web.Application([
            (r'.*/env', EnvHandler),
            (r'.*/api/(.*)', APIHandler),
            (r'.*/whoami/?', WhoAmIHandler),
            (r'.*/owhoami/?', OWhoAmIHandler),
            (r'.*/oauth_callback', HubOAuthCallbackHandler),
            (r'.*', EchoHandler),
        ], cookie_secret=os.urandom(32))

        server = httpserver.HTTPServer(app)
        server.listen(url.port, url.hostname)
    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print('\nInterrupted')


if __name__ == '__main__':
    from tornado.options import parse_command_line
    parse_command_line()
    main()
