"""extra traitlets"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from IPython.utils.traitlets import Unicode

class URLPrefix(Unicode):
    def validate(self, obj, value):
        u = super().validate(obj, value)
        if not u.startswith('/'):
            u = '/' + u
        if not u.endswith('/'):
            u = u + '/'
        return u
