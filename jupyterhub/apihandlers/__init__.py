from . import auth, groups, hub, proxy, roles, services, users
from .base import *

default_handlers = []
for mod in (auth, hub, proxy, users, groups, services, roles):
    default_handlers.extend(mod.default_handlers)
