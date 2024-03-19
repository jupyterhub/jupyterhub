"""
Traitlets that are used in JupyterHub
"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import sys

# See compatibility note on `group` keyword in https://docs.python.org/3/library/importlib.metadata.html#entry-points
if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

from traitlets import Integer, List, TraitError, TraitType, Type, Undefined, Unicode


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

    def __init__(self, default_value=Undefined, **kwargs):
        kwargs.setdefault('minlen', 1)
        if isinstance(default_value, str):
            default_value = [default_value]
        if default_value is not Undefined and (
            not (default_value is None and not kwargs.get("allow_none", False))
        ):
            kwargs["default_value"] = default_value
        super().__init__(Unicode(), **kwargs)

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
        'T': 1024 * 1024 * 1024 * 1024,
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
        if isinstance(value, (int, float)):
            return int(value)

        try:
            num = float(value[:-1])
        except ValueError:
            raise TraitError(
                f'{value} is not a valid memory specification. Must be an int or a string with suffix K, M, G, T'
            )
        suffix = value[-1]
        if suffix not in self.UNIT_SUFFIXES:
            raise TraitError(
                f'{value} is not a valid memory specification. Must be an int or a string with suffix K, M, G, T'
            )
        else:
            return int(float(num) * self.UNIT_SUFFIXES[suffix])


class Callable(TraitType):
    """
    A trait which is callable.

    Classes are callable, as are instances
    with a __call__() method.
    """

    info_text = 'a callable'

    def validate(self, obj, value):
        if callable(value):
            return value
        else:
            self.error(obj, value)


class EntryPointType(Type):
    """Entry point-extended Type

    classes can be registered via entry points
    in addition to standard 'mypackage.MyClass' strings
    """

    _original_help = ''

    def __init__(self, *args, entry_point_group, **kwargs):
        self.entry_point_group = entry_point_group
        super().__init__(*args, **kwargs)

    @property
    def help(self):
        """Extend help by listing currently installed choices"""
        chunks = [self._original_help]
        chunks.append("Currently installed: ")
        for key, entry_point in self.load_entry_points().items():
            chunks.append(f"  - {key}: {entry_point.module}.{entry_point.attr}")
        return '\n'.join(chunks)

    @help.setter
    def help(self, value):
        self._original_help = value

    def load_entry_points(self):
        """Load my entry point group

        Returns a dict whose keys are lowercase entrypoint names
        """
        return {
            entry_point.name.lower(): entry_point
            for entry_point in entry_points(group=self.entry_point_group)
        }

    def validate(self, obj, value):
        if isinstance(value, str):
            # first, look up in entry point registry
            registry = self.load_entry_points()
            key = value.lower()
            if key in registry:
                value = registry[key].load()
        return super().validate(obj, value)
