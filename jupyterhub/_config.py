"""Utilites for getting the resolved Hub config

Used in the /api/info endpoint
"""

from dataclasses import dataclass, field
from typing import Optional

from traitlets.log import get_logger

from jupyterhub import crypto
from jupyterhub.user import User


@dataclass
class _MockORMUser:
    """Mock orm.User API, so we can instantiate a Spawner without a real user"""

    id: int = 0
    name: str = "username"
    admin: bool = False
    encrypted_auth_state: Optional[bytes] = None
    state: dict = field(default_factory=dict)

    # relationships likely to be used
    orm_spawners: dict = field(default_factory=dict)
    groups: list = field(default_factory=list)

    # other fields technically exist, but shouldn't be accessed by Spawners
    # these likely won't be exposed when we separate Spawners from db access
    created = None
    last_activity = None
    cookie_id: str = ""
    roles: list = field(default_factory=list)


class _MockUser(User):
    """Mock orm.User API, so we can instantiate a Spawner without a real user"""

    def _new_orm_spawner(self, servername=""):
        pass


class _MockDB:
    """Mock out deprecated db access"""

    def add(self, obj):
        pass

    def commit(self):
        pass


def _mock_spawner(spawner_class, config):
    user = _MockUser(orm_user=_MockORMUser(), db=_MockDB())
    try:
        return spawner_class(config=config)
    except Exception:
        return


def get_resolved_config(hub, trait_filters=()):
    """Return configuration as a dict

    trait_filters is a sequence of strings of the form 'ClassName' or 'ClassName.trait_name'.
    """
    log = get_logger()
    full_class_filters = set()
    class_trait_filters = {}
    for f in trait_filters:
        if "." not in f:
            full_class_filters.add(f)
        else:
            cls_name, _, trait_name = f.partition(".")
            if cls_name not in full_class_filters:
                cls_filters = class_trait_filters.setdefault(cls_name, set())
                cls_filters.add(trait_name)

    all_classes = full_class_filters | set(class_trait_filters.keys())

    # track any sections we didn't look at via instances
    unused_sections = set() | all_classes

    def _get_config_for_object(obj):
        nonlocal unused_sections

        config_class_names = set(obj.__class__.section_names())
        unused_sections -= config_class_names

        include_all = bool(full_class_filters.intersection(config_class_names))

        include_trait_names = set()
        if not include_all:
            for cls_name in config_class_names:
                if cls_name in class_trait_filters:
                    include_trait_names |= class_trait_filters[cls_name]

        cls_config = {}
        for name in obj.traits(config=True):
            if include_all or name in include_trait_names:
                try:
                    value = getattr(obj, name)
                except Exception as e:
                    log.error(
                        f"Failed to get config value {cls_name}.{trait_name}: {e}"
                    )
                    value = "<unknown>"
                cls_config[name] = value

        if cls_config:
            resolved_config[obj.__class__.__name__] = cls_config

    resolved_config = {}

    # this should be a list of all configurable instances
    # we can't know exactly what they are, though (e.g. multiple Configurable classes used by a Spawner)
    configurables = [hub, hub.authenticator, hub.proxy]
    if hub.authenticator.enable_auth_state:
        configurables.append(crypto.CryptKeeper.instance())

    # check if spawner is requested, since it requires instantiating a mock object
    spawner_classes = set(hub.spawner_class.section_names())
    if spawner_classes & all_classes:
        try:
            spawner = _mock_spawner(hub.spawner_class, config=hub.config)
        except Exception as e:
            log.error(f"Failed to instantiate mock Spawner for inspection: {e}")
        else:
            configurables.append(spawner)

    for obj in configurables:
        _get_config_for_object(obj)

    # report any unused sections from the config object
    for section in unused_sections:
        log.warning(f"Unrecognized config section: {section}")
        if section in full_class_filters:
            if section in hub.config:
                resolved_config[section] = dict(hub.config[section])

    return resolved_config
