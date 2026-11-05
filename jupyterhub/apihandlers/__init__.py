from . import auth, groups, hub, oidc, proxy, services, shares, users
from .base import *  # noqa

default_handlers = []
for mod in (auth, hub, proxy, users, groups, services, shares, oidc):
    default_handlers.extend(mod.default_handlers)
