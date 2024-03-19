from . import auth, groups, hub, proxy, services, shares, users
from .base import *  # noqa

default_handlers = []
for mod in (auth, hub, proxy, users, groups, services, shares):
    default_handlers.extend(mod.default_handlers)
