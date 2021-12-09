from . import auth
from . import groups
from . import hub
from . import proxy
from . import services
from . import users
from .base import *

default_handlers = []
for mod in (auth, hub, proxy, users, groups, services):
    default_handlers.extend(mod.default_handlers)
