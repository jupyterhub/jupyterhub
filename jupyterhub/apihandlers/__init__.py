from .base import *
from . import auth, hub, proxy, users, groups, services

default_handlers = []
for mod in (auth, hub, proxy, users, groups, services):
    default_handlers.extend(mod.default_handlers)
