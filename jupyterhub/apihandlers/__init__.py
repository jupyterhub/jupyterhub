from . import auth, groups, hub, proxy, services, users
from .base import *

default_handlers = []
for mod in (auth, hub, proxy, users, groups, services):
    default_handlers.extend(mod.default_handlers)
