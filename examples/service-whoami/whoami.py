"""An example service authenticating with the Hub.

This serves `/hub/whoami/`, authenticated with the Hub, showing the user their own info.
"""
from getpass import getuser
import json
import os

import requests

from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.web import RequestHandler, Application, authenticated

from jupyterhub.services.auth import HubAuthenticated, HubAuth


class WhoAmIHandler(HubAuthenticated, RequestHandler):
    hub_users = {getuser()} # the users allowed to access me

    def initialize(self, hub_auth):
        super().initialize()
        self.hub_auth = hub_auth

    @authenticated
    def get(self):
        user_model = self.get_current_user()
        self.set_header('content-type', 'application/json')
        self.write(json.dumps(user_model, indent=1, sort_keys=True))

def add_route():
    # add myself to the proxy
    # TODO: this will be done by the Hub when the Hub gets service config
    requests.post('http://127.0.0.1:8001/api/routes/hub/whoami',
         data=json.dumps({
             'target': 'http://127.0.0.1:9999',
         }),
         headers={
             'Authorization': 'token %s' % os.environ['CONFIGPROXY_AUTH_TOKEN'],
         }
    )

def main():
    # FIXME: remove when we can declare routes in Hub config
    add_route()
    
    hub_auth = HubAuth(
        cookie_name='jupyter-hub-token',
        api_token=os.environ['WHOAMI_HUB_API_TOKEN'],
        login_url='http://127.0.0.1:8000/hub/login',
    )
    app = Application([
        (r"/hub/whoami", WhoAmIHandler, dict(hub_auth=hub_auth)),
    ], login_url=hub_auth.login_url)
    
    http_server = HTTPServer(app)
    http_server.listen(9999)
    IOLoop.current().start()

if __name__ == '__main__':
    main()