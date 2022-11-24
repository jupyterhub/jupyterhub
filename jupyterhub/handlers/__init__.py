from . import base, login, metrics, pages
from .base import *  # noqa
from .login import *  # noqa

default_handlers = []
for mod in (base, pages, login, metrics):
    default_handlers.extend(mod.default_handlers)
