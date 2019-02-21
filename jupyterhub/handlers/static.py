# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import os

from tornado.web import StaticFileHandler


class CacheControlStaticFilesHandler(StaticFileHandler):
    """StaticFileHandler subclass that sets Cache-Control: no-cache without `?v=`
    
    rather than relying on default browser cache behavior.
    """

    def compute_etag(self):
        return None

    def set_extra_headers(self, path):
        if "v" not in self.request.arguments:
            self.add_header("Cache-Control", "no-cache")


class LogoHandler(StaticFileHandler):
    """A singular handler for serving the logo."""

    def get(self):
        return super().get('')

    @classmethod
    def get_absolute_path(cls, root, path):
        """We only serve one file, ignore relative path"""
        return os.path.abspath(root)
