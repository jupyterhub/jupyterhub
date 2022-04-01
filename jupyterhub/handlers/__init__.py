from . import base, login, metrics, pages
from .base import *
from .login import *

default_handlers = []
for mod in (base, pages, login, metrics):
    default_handlers.extend(mod.default_handlers)
