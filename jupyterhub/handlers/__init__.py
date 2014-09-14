from .base import *
from .login import *

from . import base, login

default_handlers = []
for mod in (base, login):
    default_handlers.extend(mod.default_handlers)
