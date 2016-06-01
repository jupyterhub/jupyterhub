from .base import *
from .auth import *
from .hub import *
from .proxy import *
from .users import *
from .groups import *
from . import auth, hub, proxy, users

default_handlers = []
for mod in (auth, hub, proxy, users, groups):
    default_handlers.extend(mod.default_handlers)
