# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from tornado.web import StaticFileHandler

class CacheControlStaticFilesHandler(StaticFileHandler):
    """StaticFileHandler subclass that sets Cache-Control: no-cache without `?v=`
    
    rather than relying on default browser cache behavior.
    """
    def set_extra_headers(self, path):
        if "v" not in self.request.arguments:
            self.add_header("Cache-Control", "no-cache")
    