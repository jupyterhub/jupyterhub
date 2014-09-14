from .base import *
from .auth import *
from .users import *

from . import auth, users

default_handlers = []
for mod in (auth, users):
    default_handlers.extend(mod.default_handlers)
