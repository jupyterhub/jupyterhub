import pytest

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
