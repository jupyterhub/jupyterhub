# Test one-off migrations
# Currently only relevant for named servers

import pytest
from traitlets.config import Config

from .. import orm
from ..app import JupyterHub
from ..utils import utcnow
from .populate_db import populate_db


@pytest.mark.parametrize(
    "allow_existing_invalid_named_servers",
    ["allow-start", "allow-delete", "autorename"],
)
async def test_named_server_migration(tmpdir, allow_existing_invalid_named_servers):
    tmpdir.chdir()

    db_url = 'sqlite:///jupyterhub.sqlite'
    populate_db(db_url)

    cfg = Config()
    cfg.JupyterHub.db_url = db_url
    cfg.JupyterHub.authenticator_class = "dummy"
    cfg.JupyterHub.allow_existing_invalid_named_servers = (
        allow_existing_invalid_named_servers
    )
    db = orm.new_session_factory(db_url)()

    server_names = [
        "a-b-c",
        "a-b-c🐧",
        "\\ a 🐧 -",
        "$p~c|a! ch@rs",
        "abc",
        "running €",
    ]
    if allow_existing_invalid_named_servers == "autorename":
        expected_server_names = [
            "a-b-c",
            # Clashes, so has a hash
            "a-b-c-3d9e03d4",
            "a",
            "p-c-a-ch-rs",
            "abc",
            # Don't rename running server
            "running €",
        ]
        expected_display_names = [
            None,
            "a-b-c🐧",
            "\\ a 🐧 -",
            "$p~c|a! ch@rs",
            None,
            None,
        ]
    else:
        expected_server_names = server_names
        expected_display_names = [None] * 6

    orm_user = orm.User(name="test")
    db.add(orm_user)

    for s in server_names:
        if s.startswith("running"):
            orm_spawner = orm.Spawner(name=s, user=orm_user, started=utcnow())
        else:
            orm_spawner = orm.Spawner(name=s, user=orm_user)
        db.add(orm_spawner)

    db.commit()

    hub = JupyterHub(config=cfg)
    await hub.initialize([])

    # JupyterHub sets expire_on_commit=False
    db.expire_all()

    spawner_names = sorted((s.name, s.display_name) for s in db.query(orm.Spawner))

    # populate_db adds 2 default servers for other users
    assert len(spawner_names) == 2 + 6
    assert spawner_names[:2] == [('', None), ('', None)]
    for s, d in zip(expected_server_names, expected_display_names):
        assert (s, d) in spawner_names
