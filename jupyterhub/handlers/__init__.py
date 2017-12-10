from .base import *
from .login import *

from . import base, pages, login, metrics

default_handlers = []
for mod in (base, pages, login, metrics):
    default_handlers.extend(mod.default_handlers)
