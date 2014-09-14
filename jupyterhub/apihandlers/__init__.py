from . import auth, users
from .auth import *
from .users import *

default_handlers = []
for mod in (auth, users):
    default_handlers.extend(mod.default_handlers)
