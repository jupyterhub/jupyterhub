import pytest

from .. import orm
from ..user import UserDict
from .utils import add_user


@pytest.mark.parametrize("attr", ["self", "id", "name"])
async def test_userdict_get(db, attr):
    u = add_user(db, name="rey", app=False)
    userdict = UserDict(db_factory=lambda: db, settings={})

    if attr == "self":
        key = u
    else:
        key = getattr(u, attr)

    # `in` checks cache only
    assert key not in userdict
    assert userdict.get(key)
    assert userdict.get(key).id == u.id
    # `in` should find it now
    assert key in userdict


@pytest.mark.parametrize(
    "group_names",
    [
        ["isin1", "isin2"],
        ["isin1"],
        ["notin", "isin1"],
        ["new-group", "isin1"],
        [],
    ],
)
def test_sync_groups(app, user, group_names):
    expected = sorted(group_names)
    db = app.db
    db.add(orm.Group(name="notin"))
    in_groups = [orm.Group(name="isin1"), orm.Group(name="isin2")]
    for group in in_groups:
        db.add(group)
    db.commit()
    user.groups = in_groups
    db.commit()
    user.sync_groups(group_names)
    assert not app.db.dirty
    after_groups = sorted(g.name for g in user.groups)
    assert after_groups == expected
    # double-check backref
    for group in db.query(orm.Group):
        if group.name in expected:
            assert user.orm_user in group.users
        else:
            assert user.orm_user not in group.users
