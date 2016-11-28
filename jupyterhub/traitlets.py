"""
Traitlets that are used in JupyterHub
"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from traitlets import List, Unicode, Integer, TraitError


class URLPrefix(Unicode):
    def validate(self, obj, value):
        u = super().validate(obj, value)
        if not u.startswith('/'):
            u = '/' + u
        if not u.endswith('/'):
            u = u + '/'
        return u

class Command(List):
    """Traitlet for a command that should be a list of strings,
    but allows it to be specified as a single string.
    """
    def __init__(self, default_value=None, **kwargs):
        kwargs.setdefault('minlen', 1)
        if isinstance(default_value, str):
            default_value = [default_value]
        super().__init__(Unicode(), default_value, **kwargs)

    def validate(self, obj, value):
        if isinstance(value, str):
            value = [value]
        return super().validate(obj, value)


class ByteSpecification(Integer):
    """
    Allow easily specifying bytes in units of 1024 with suffixes

    Suffixes allowed are:
      - K -> Kilobyte
      - M -> Megabyte
      - G -> Gigabyte
      - T -> Terabyte
    """

    UNIT_SUFFIXES = {
        'K': 1024,
        'M': 1024 * 1024,
        'G': 1024 * 1024 * 1024,
        'T': 1024 * 1024 * 1024 * 1024
    }

    # Default to allowing None as a value
    allow_none = True

    def validate(self, obj, value):
        """
        Validate that the passed in value is a valid memory specification

        It could either be a pure int, when it is taken as a byte value.
        If it has one of the suffixes, it is converted into the appropriate
        pure byte value.
        """
        if isinstance(value, int):
            return value
        num = value[:-1]
        suffix = value[-1]
        if not num.isdigit() and suffix not in ByteSpecification.UNIT_SUFFIXES:
            raise TraitError('{val} is not a valid memory specification. Must be an int or a string with suffix K, M, G, T'.format(val=value))
        else:
            return int(num) * ByteSpecification.UNIT_SUFFIXES[suffix]
