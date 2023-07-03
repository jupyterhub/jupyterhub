from datetime import timedelta

import pytest

from jupyterhub import orm

from .conftest import new_username
from .utils import add_user


@pytest.fixture
def share(app, user):
    db = app.db
    spawner = user.spawner.orm_spawner
    owner = user.orm_user
    share_with = add_user(db, name=new_username("share_with"))
    filter_ = f"server={owner.name}/{spawner.name}"
    scopes = [f"access:servers!{filter_}"]
    yield orm.Share.grant(db, spawner, share_with, scopes=scopes)
    for share in db.query(orm.Share):
        db.delete(share)
    user = orm.User.find(db, name=share_with.name)
    if user:
        db.delete(user)
    db.commit()


def test_create_share(app, user):
    db = app.db
    spawner = user.spawner.orm_spawner
    owner = user.orm_user
    share_with = add_user(db, name=new_username("share_with"))
    scopes = [f"access:servers!server={owner.name}/{spawner.name}"]
    before = orm.Share.now()
    share = orm.Share.grant(db, spawner, share_with, scopes=scopes)
    after = orm.Share.now()
    assert share.scopes == scopes
    assert share.owner is owner
    assert share.spawner is spawner
    assert share.user is share_with
    assert share.created_at
    assert before <= share.created_at <= after
    assert share in share_with.shared_with_me
    assert share in spawner.shares
    assert share in owner.shares
    assert share not in share_with.shares
    assert share not in owner.shared_with_me
    db.delete(share_with)
    db.commit()


def test_update_share(app, share):
    db = app.db
    # shift into past
    share.created_at -= timedelta(hours=1)
    created_at = share.created_at
    db.commit()

    # grant additional scopes
    more_scopes = [f"read:servers!server={share.owner.name}/{share.spawner.name}"]
    all_scopes = sorted(share.scopes + more_scopes)
    share2 = orm.Share.grant(db, share.spawner, share.user, scopes=more_scopes)
    assert share2 is share
    assert share.created_at == created_at
    assert share.scopes == all_scopes

    # fully overlapping scopes
    share3 = orm.Share.grant(db, share.spawner, share.user, scopes=share.scopes[:1])
    assert share3 is share
    assert share.created_at == created_at
    assert share.scopes == all_scopes


@pytest.mark.parametrize(
    "to_delete",
    [
        "owner",
        "spawner",
        "share_with_user",
        "share_with_group",
    ],
)
def test_share_delete_cascade(to_delete, app, user, group):
    db = app.db
    if "group" in to_delete:
        share_with = group
    else:
        share_with = add_user(db, app, name=new_username("share_with")).orm_user
    spawner = user.spawner.orm_spawner
    owner = user.orm_user
    scopes = [f"access:servers!server={owner.name}/{spawner.name}"]
    assert spawner.name is not None
    assert spawner.user.name
    assert share_with.name
    share = orm.Share.grant(db, spawner, share_with, scopes=scopes)
    assert share in share_with.shared_with_me
    share_id = share.id
    if to_delete == "owner":
        app.users.delete(owner)
        assert share_with.shared_with_me == []
    elif to_delete == "spawner":
        # pass
        db.delete(spawner)
        user.spawners.pop(spawner.name)
        db.commit()
        assert owner.shares == []
        assert share_with.shared_with_me == []
    elif to_delete == "share_with_user":
        app.users.delete(share_with)
        assert owner.shares == []
        assert spawner.shares == []
    elif to_delete == "share_with_group":
        db.delete(share_with)
        db.commit()
        assert owner.shares == []
        assert spawner.shares == []
    else:
        raise ValueError(f"unexpected {to_delete=}")
    # make sure it's gone
    assert db.query(orm.Share).filter_by(id=share_id).one_or_none() is None


def test_share_allowed():
    pass


def test_share_missing_user():
    pass


def test_share_missing_spawner():
    pass


def test_share_code():
    pass


# API tests


def test_share_create_api():
    pass


def test_share_list_user():
    pass


def test_share_list_group():
    pass


def test_share_list_server():
    pass
