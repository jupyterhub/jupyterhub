from .base import *
from .auth import *
from .proxy import *
from .users import *

from . import auth, proxy, users

default_handlers = []
for mod in (auth, proxy, users):
    default_handlers.extend(mod.default_handlers)
