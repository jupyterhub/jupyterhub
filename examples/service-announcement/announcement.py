import argparse
import datetime
import json
import os

from tornado import escape
from tornado import ioloop
from tornado import web

from jupyterhub.services.auth import HubAuthenticated


class AnnouncementRequestHandler(HubAuthenticated, web.RequestHandler):
    """Dynamically manage page announcements"""

    hub_users = []
    allow_admin = True

    def initialize(self, storage):
        """Create storage for announcement text"""
        self.storage = storage

    @web.authenticated
    def post(self):
        """Update announcement"""
        user = self.get_current_user()
        doc = escape.json_decode(self.request.body)
        self.storage["announcement"] = doc["announcement"]
        self.storage["timestamp"] = datetime.datetime.now().isoformat()
        self.storage["user"] = user["name"]
        self.write_to_json(self.storage)

    def get(self):
        """Retrieve announcement"""
        self.write_to_json(self.storage)

    @web.authenticated
    def delete(self):
        """Clear announcement"""
        self.storage["announcement"] = ""
        self.write_to_json(self.storage)

    def write_to_json(self, doc):
        """Write dictionary document as JSON"""
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(escape.utf8(json.dumps(doc)))


def main():
    args = parse_arguments()
    application = create_application(**vars(args))
    application.listen(args.port)
    ioloop.IOLoop.current().start()


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--api-prefix",
        "-a",
        default=os.environ.get("JUPYTERHUB_SERVICE_PREFIX", "/"),
        help="application API prefix",
    )
    parser.add_argument(
        "--port", "-p", default=8888, help="port for API to listen on", type=int
    )
    return parser.parse_args()


def create_application(api_prefix="/", handler=AnnouncementRequestHandler, **kwargs):
    storage = dict(announcement="", timestamp="", user="")
    return web.Application([(api_prefix, handler, dict(storage=storage))])


if __name__ == "__main__":
    main()
