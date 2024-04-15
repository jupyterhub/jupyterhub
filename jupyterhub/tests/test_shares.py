import json
from datetime import timedelta
from functools import partial
from unittest import mock
from urllib.parse import parse_qs, urlparse, urlunparse

import pytest
from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date
from tornado.httputil import url_concat

from jupyterhub import orm, scopes
from jupyterhub.utils import url_path_join, utcnow

from .conftest import new_group_name, new_username
from .utils import add_user, api_request, async_requests, get_page, public_url


@pytest.fixture
def share_user(app):
    """The user to be shared with"""
    yield add_user(app.db, name=new_username("share_with"))


@pytest.fixture
def share(app, user, share_user):
    """Share access to `user`'s default server with `share_user`"""
    db = app.db
    spawner = user.spawner.orm_spawner
    owner = user.orm_user
    filter_ = f"server={owner.name}/{spawner.name}"
    scopes = [f"access:servers!{filter_}"]
    yield orm.Share.grant(db, spawner, share_user, scopes=scopes)


@pytest.fixture
def group_share(app, user, group, share_user):
    """Share with share_user via group membership"""
    db = app.db
    app.db.commit()
    spawner = user.spawner.orm_spawner
    owner = user.orm_user
    filter_ = f"server={owner.name}/{spawner.name}"
    scopes = [f"read:servers!{filter_}"]
    group.users.append(share_user)
    yield orm.Share.grant(db, spawner, group, scopes=scopes)


@pytest.fixture
def populate_shares(app, user, group, share_user):
    group_a = orm.Group(name=new_group_name("a"))
    group_b = orm.Group(name=new_group_name("b"))
    group_c = orm.Group(name=new_group_name("c"))
    app.db.add(group_a)
    app.db.add(group_b)
    app.db.add(group_c)
    app.db.commit()
    in_a = add_user(app.db, name=new_username("in-a"))
    in_a_b = add_user(app.db, name=new_username("in-a-b"))
    in_b = add_user(app.db, name=new_username("in-b"))
    not_in = add_user(app.db, name=new_username("not-in"))

    group_a.users = [in_a, in_a_b]
    group_b.users = [in_b, in_a_b]
    app.db.commit()

    user_1 = add_user(app.db, name=new_username("server"))
    user_2 = add_user(app.db, name=new_username("server"))
    user_3 = add_user(app.db, name=new_username("server"))
    user_4 = add_user(app.db, name=new_username("server"))

    # group a has access to user_1
    # group b has access to user_2
    # both groups have access to user_3
    # user in-a also has access to user_4
    orm.Share.grant(
        app.db,
        app.users[user_1].spawner.orm_spawner,
        group_a,
    )
    orm.Share.grant(
        app.db,
        app.users[user_2].spawner.orm_spawner,
        group_b,
    )
    orm.Share.grant(
        app.db,
        app.users[user_3].spawner.orm_spawner,
        group_a,
    )
    orm.Share.grant(
        app.db,
        app.users[user_3].spawner.orm_spawner,
        group_b,
    )
    orm.Share.grant(
        app.db,
        app.users[user_4].spawner.orm_spawner,
        in_a,
    )
    orm.Share.grant(
        app.db,
        app.users[user_4].spawner.orm_spawner,
        not_in,
    )

    # return a dict showing who should have access to what
    return {
        "users": {
            in_a.name: [user_1.name, user_3.name, user_4.name],
            in_b.name: [user_2.name, user_3.name],
            # shares are _not_ deduplicated if granted
            # both via user and group
            in_a_b.name: [user_1.name, user_2.name, user_3.name, user_3.name],
            not_in.name: [user_4.name],
        },
        "groups": {
            group_a.name: [user_1.name, user_3.name],
            group_b.name: [user_2.name, user_3.name],
            group_c.name: [],
        },
    }


def expand_scopes(scope_str, user, group=None, share_with=None):
    """utility to expand scopes used in parametrized tests

    Turns "read:users!user=USER,shares!group=SHARE_WITH"
    into
        [
            "read:users!user=username",
            "shares!group=groupname",
        ]
    """
    scopes = []
    replacements = {}

    def _get_name(str_or_obj):
        """Allow a string name or an object with a name attribute

        string names are used for tests where something doesn't exist
        """
        if isinstance(str_or_obj, str):
            return str_or_obj
        else:
            return str_or_obj.name

    username = _get_name(user)
    replacements["USER"] = username
    replacements["SERVER"] = username + "/"
    if group:
        replacements["GROUP"] = _get_name(group)
    if share_with:
        replacements["SHARE_WITH"] = _get_name(share_with)
    for scope in scope_str.split(","):
        for a, b in replacements.items():
            scope = scope.replace(a, b)
        scopes.append(scope)
    return scopes


@pytest.mark.parametrize(
    "share_with", ["user", pytest.param("group", id="share_with=group")]
)
def test_create_share(app, user, share_user, group, share_with):
    db = app.db
    spawner = user.spawner.orm_spawner
    owner = user.orm_user
    share_attr = share_with
    if share_with == "group":
        share_with = group
    elif share_with == "user":
        share_with = share_user
    scopes = [f"access:servers!server={owner.name}/{spawner.name}"]
    before = orm.Share.now()
    share = orm.Share.grant(db, spawner, share_with, scopes=scopes)
    after = orm.Share.now()
    assert share.scopes == scopes
    assert share.owner is owner
    assert share.spawner is spawner
    assert getattr(share, share_attr) is share_with
    assert share.created_at
    assert before <= share.created_at <= after
    assert share in share_with.shared_with_me
    assert share in spawner.shares
    assert share in owner.shares
    if share_attr == 'user':
        assert share not in share_with.shares
    assert share not in owner.shared_with_me
    # compute repr for coverage
    repr(share)
    db.delete(share_with)
    db.commit()


def test_create_share_bad(app, user, share_user, mockservice):
    db = app.db
    service = mockservice
    spawner = user.spawner.orm_spawner
    owner = user.orm_user
    scopes = [f"access:servers!server={owner.name}/{spawner.name}"]
    with pytest.raises(ValueError):
        orm.Share.grant(db, spawner, share_user, scopes=[])
    with pytest.raises(TypeError):
        orm.Share.grant(db, spawner, service, scopes=scopes)


def test_update_share(app, share):
    db = app.db
    # shift into past
    share.created_at -= timedelta(hours=1)
    created_at = share.created_at
    db.commit()

    # grant additional scopes
    filter = f"server={share.owner.name}/{share.spawner.name}"
    more_scopes = [f"read:servers!{filter}"]
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

    # revoke scopes not held
    share4 = orm.Share.revoke(
        db,
        share.spawner,
        share.user,
        scopes=[f"admin:servers!{filter}"],
    )
    assert share4 is share
    assert share.created_at == created_at
    assert share.scopes == all_scopes

    # revoke some scopes
    share5 = orm.Share.revoke(
        db,
        share.spawner,
        share.user,
        scopes=all_scopes[:1],
    )
    remaining_scopes = all_scopes[1:]
    assert share5 is share
    assert share.created_at == created_at
    assert share.scopes == remaining_scopes

    # revoke remaining scopes
    share5 = orm.Share.revoke(
        db,
        share.spawner,
        share.user,
        scopes=remaining_scopes,
    )
    assert share5 is None
    found_share = orm.Share.find(db, spawner=share.spawner, share_with=share.user)
    assert found_share is None


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


def test_share_scopes(app, share_user, share):
    db = app.db
    user_scopes = scopes.get_scopes_for(share_user)
    assert set(share.scopes).issubset(user_scopes)
    # delete share, no longer have scopes
    db.delete(share)
    db.commit()
    user_scopes = scopes.get_scopes_for(share_user)
    assert not set(share.scopes).intersection(user_scopes)


def test_share_group_scopes(app, share_user, group_share):
    # make sure share is actually in the group (make sure group_share fixture worked)
    db = app.db
    share = group_share
    assert group_share.group in share_user.groups
    user_scopes = scopes.get_scopes_for(share_user)
    assert set(share.scopes).issubset(user_scopes)
    # delete share, no longer have scopes
    db.delete(share)
    db.commit()
    user_scopes = scopes.get_scopes_for(share_user)
    assert not set(share.scopes).intersection(user_scopes)


def test_share_code(app, user, share_user):
    spawner = user.spawner.orm_spawner
    user = spawner.user
    code_scopes = sorted(
        [
            f"read:servers!server={user.name}/",
            f"access:servers!server={user.name}/",
        ]
    )
    orm_code, code = orm.ShareCode.new(
        app.db,
        spawner,
        scopes=code_scopes,
    )
    assert sorted(orm_code.scopes) == code_scopes
    assert orm_code.owner is user
    assert orm_code.spawner is spawner
    assert orm_code in spawner.share_codes
    assert orm_code in user.share_codes

    share_with_scopes = scopes.get_scopes_for(share_user)
    for scope in code_scopes:
        assert scope not in share_with_scopes

    assert orm_code.exchange_count == 0
    assert orm_code.last_exchanged_at is None
    # do it twice, shouldn't change anything
    orm_code.exchange(share_user)
    assert orm_code.exchange_count == 1
    assert orm_code.last_exchanged_at is not None
    now = orm_code.now()
    assert now - timedelta(10) <= orm_code.last_exchanged_at <= now + timedelta(10)

    share_with_scopes = scopes.get_scopes_for(share_user)
    for scope in code_scopes:
        assert scope in share_with_scopes


def test_share_code_expires(app, user, share_user):
    db = app.db
    spawner = user.spawner.orm_spawner
    user = spawner.user
    orm_code, code = orm.ShareCode.new(
        db,
        spawner,
        scopes=[
            f"access:servers!server={user.name}/",
        ],
    )
    # check expiration
    assert orm_code.expires_at
    now = orm_code.now()
    assert (
        now - timedelta(10)
        <= orm_code.expires_at
        <= now + timedelta(seconds=orm.ShareCode.default_expires_in + 10)
    )
    orm.ShareCode.purge_expired(db)
    found = orm.ShareCode.find(db, code=code)
    assert found
    assert found.id == orm_code.id

    with mock.patch(
        'jupyterhub.orm.ShareCode.now', staticmethod(lambda: now + timedelta(hours=1))
    ):
        orm.ShareCode.purge_expired(db)
        found = orm.ShareCode.find(db, code=code)
        assert found
        assert found.id == orm_code.id

    with mock.patch(
        'jupyterhub.orm.ShareCode.now', staticmethod(lambda: now + timedelta(hours=25))
    ):
        found = orm.ShareCode.find(db, code=code)
        assert found is None
        # try exchanging expired code
        with pytest.raises(ValueError):
            orm_code.exchange(share_user)

    # expired code, should have been deleted
    found = orm.ShareCode.find(db, code=code)
    assert found is None
    assert db.query(orm.ShareCode).filter_by(id=orm_code.id).one_or_none() is None


# API tests


@pytest.mark.parametrize(
    "kind",
    [
        ("user"),
        (pytest.param("group", id="kind=group")),
    ],
)
async def test_shares_api_user_group_doesnt_exist(
    app,
    user,
    group,
    share_user,
    kind,
):
    # make sure default spawner exists
    spawner = user.spawner  # noqa
    body = {}
    if kind == "user":
        body["user"] = "nosuchuser"
    elif kind == "group":
        body["group"] = "nosuchgroup"

    r = await api_request(
        app, f"/shares/{user.name}/", method="post", data=json.dumps(body)
    )
    assert r.status_code == 400


@pytest.mark.parametrize(
    "which",
    [
        ("user"),
        ("server"),
    ],
)
async def test_shares_api_target_doesnt_exist(
    app,
    user,
    group,
    share_user,
    which,
):
    # make sure default spawner exists
    if which == "server":
        share_path = f"/shares/{user.name}/nosuchserver"
    elif which == "user":
        share_path = "/shares/nosuchuser/"
    body = {"user": share_user.name}

    r = await api_request(app, share_path, method="post", data=json.dumps(body))
    assert r.status_code == 404


@pytest.mark.parametrize(
    "have_scopes, share_scopes, with_user, with_group, status",
    [
        (None, None, True, False, 200),
        ("shares", None, True, False, 403),
        (
            "shares!server=SERVER,servers!server=SERVER,read:users:name!user=SHARE_WITH",
            "read:servers!server=SERVER,access:servers!server=SERVER",
            True,
            False,
            200,
        ),
        (None, "read:servers!server=other/", False, True, 400),
        (
            "shares,access:servers,read:users:name",
            "admin:servers!server=SERVER",
            False,
            True,
            403,
        ),
        (None, None, False, False, 400),
        (None, None, "nosuchuser", False, 400),
        (None, None, False, "nosuchgroup", 400),
        (None, None, True, True, 400),
        (None, None, True, False, 200),
    ],
)
async def test_shares_api_create(
    app,
    user,
    group,
    share_user,
    create_user_with_scopes,
    have_scopes,
    share_scopes,
    with_user,
    with_group,
    status,
):
    # make sure default spawner exists
    spawner = user.spawner  # noqa
    body = {}
    share_with = share_user
    if with_user:
        body["user"] = share_user.name if with_user == True else with_user
    if with_group:
        body["group"] = group.name if with_group == True else with_group
        share_with = group
    _expand_scopes = partial(expand_scopes, user=user, share_with=share_with)

    expected_scopes = _expand_scopes("access:servers!server=SERVER")
    if share_scopes:
        share_scopes = _expand_scopes(share_scopes)
        expected_scopes.extend(share_scopes)
        body["scopes"] = share_scopes

    expected_scopes = sorted(set(expected_scopes))

    if have_scopes is None:
        # default: needed permissions
        have_scopes = "shares,read:users:name,read:groups:name"

    requester = create_user_with_scopes(*_expand_scopes(have_scopes))

    r = await api_request(
        app,
        f"/shares/{user.name}/",
        method="post",
        data=json.dumps(body),
        name=requester.name,
    )
    assert r.status_code == status
    if r.status_code < 300:
        share_model = r.json()
        assert "scopes" in share_model
        assert sorted(share_model["scopes"]) == expected_scopes


@pytest.mark.parametrize(
    "have_scopes, before_scopes, revoke_scopes, after_scopes, with_user, with_group, status",
    [
        ("read:shares", None, None, None, True, False, 403),
        ("shares", None, None, None, True, False, 200),
        ("shares!user=USER", None, None, None, False, True, 200),
        (None, "read:servers!server=SERVER", None, None, True, False, 200),
        (
            None,
            "access:servers!server=SERVER",
            "read:servers!server=SERVER",
            "access:servers!server=SERVER",
            True,
            False,
            200,
        ),
        (None, None, None, None, "nosuchuser", False, 200),
        (None, None, None, None, False, "nosuchgroup", 200),
        (None, None, None, None, False, False, 400),
        (None, None, None, None, True, True, 400),
    ],
)
async def test_shares_api_revoke(
    app,
    user,
    group,
    share_user,
    create_user_with_scopes,
    have_scopes,
    before_scopes,
    revoke_scopes,
    after_scopes,
    with_user,
    with_group,
    status,
):
    db = app.db
    # make sure default spawner exists
    spawner = user.spawner.orm_spawner  # noqa
    body = {}
    share_with = share_user
    if with_user:
        body["user"] = share_user.name if with_user == True else with_user
    if with_group:
        body["group"] = group.name if with_group == True else with_group
        share_with = group
    _expand_scopes = partial(expand_scopes, user=user, share_with=share_with)

    if revoke_scopes:
        revoke_scopes = _expand_scopes(revoke_scopes)
        body["scopes"] = revoke_scopes

    if after_scopes:
        after_scopes = _expand_scopes(after_scopes)

    if before_scopes:
        orm.Share.grant(db, spawner, share_with, scopes=_expand_scopes(before_scopes))

    if have_scopes is None:
        # default: needed permissions
        have_scopes = "shares,read:users:name,read:groups:name"

    requester = create_user_with_scopes(*_expand_scopes(have_scopes))

    r = await api_request(
        app,
        f"/shares/{user.name}/",
        method="patch",
        data=json.dumps(body),
        name=requester.name,
    )
    assert r.status_code == status
    if r.status_code < 300:
        share_model = r.json()
        if not after_scopes:
            # no scopes specified, full revocation
            assert share_model == {}
            return
        assert share_model["scopes"] == after_scopes


@pytest.mark.parametrize(
    "have_scopes, status",
    [
        ("shares", 204),
        ("shares!user=USER", 204),
        ("shares!server=SERVER", 204),
        ("read:shares", 403),
        ("shares!server=USER/other", 404),
        ("shares!user=other", 404),
    ],
)
async def test_shares_api_revoke_all(
    app,
    user,
    group,
    share_user,
    create_user_with_scopes,
    have_scopes,
    status,
):
    db = app.db
    # make sure default spawner exists
    spawner = user.spawner.orm_spawner  # noqa
    orm.Share.grant(db, spawner, share_user)
    orm.Share.grant(db, spawner, group)
    _expand_scopes = partial(expand_scopes, user=user)

    if have_scopes is None:
        # default: needed permissions
        have_scopes = "shares"

    requester = create_user_with_scopes(*_expand_scopes(have_scopes))

    r = await api_request(
        app,
        f"/shares/{user.name}/",
        method="delete",
        name=requester.name,
    )
    assert r.status_code == status

    # get updated share list
    r = await api_request(
        app,
        f"/shares/{user.name}/",
    )
    share_list = r.json()

    if status >= 400:
        assert len(share_list["items"]) == 2
    else:
        assert len(share_list["items"]) == 0


@pytest.mark.parametrize(
    "kind, case",
    [
        ("users", "in-a"),
        ("users", "in-b"),
        ("users", "in-a-b"),
        ("users", "not-in"),
        ("users", "notfound"),
        ("groups", "a"),
        ("groups", "b"),
        ("groups", "c"),
        ("groups", "notfound"),
    ],
)
async def test_shared_api_list_user_group(
    app, populate_shares, create_user_with_scopes, kind, case
):
    if case == "notfound":
        name = "notfound"
    else:
        # find exact name, which will look like `{kind}-123`
        for name, server_names in populate_shares[kind].items():
            if name.rpartition("-")[0] == case:
                break
        else:
            raise ValueError(f"Did not find {case} in {populate_shares[kind].keys()}")

    r = await api_request(app, f"/{kind}/{name}/shared")
    if name == "notfound":
        assert r.status_code == 404
        return
    else:
        assert r.status_code == 200
    shares = r.json()
    found_shares = sorted(
        [share["server"]["user"]["name"] for share in shares["items"]]
    )
    expected_shares = sorted(server_names)
    assert found_shares == expected_shares


@pytest.mark.parametrize(
    "kind, have_scopes, get_status, delete_status",
    [
        ("users", "users", 403, 403),
        ("users", "read:users", 403, 403),
        ("users", "read:users!user=USER", 403, 403),
        ("users", "read:users:shares!user=SHARE_WITH", 200, 403),
        ("users", "users:shares!user=SHARE_WITH", 200, 204),
        ("users", "users:shares!user=other", 404, 404),
        ("groups", "groups", 403, 403),
        ("groups", "read:groups", 403, 403),
        ("groups", "read:groups!group=group", 403, 403),
        ("groups", "read:groups:shares!group=SHARE_WITH", 200, 403),
        ("groups", "groups:shares!group=SHARE_WITH", 200, 204),
        ("groups", "groups:shares!group=other", 404, 404),
    ],
)
async def test_single_shared_api(
    app,
    user,
    share_user,
    group,
    create_user_with_scopes,
    kind,
    have_scopes,
    get_status,
    delete_status,
):
    db = app.db
    share_user.groups.append(group)
    db.commit()
    spawner = user.spawner.orm_spawner

    if kind == "users":
        share_with = share_user
    else:
        share_with = group

    _expand_scopes = partial(expand_scopes, user=user, share_with=share_with)

    requester = create_user_with_scopes(*_expand_scopes(have_scopes))

    share_scopes = [f"access:servers!server={user.name}/"]
    share = orm.Share.grant(
        db, spawner=spawner, share_with=share_with, scopes=share_scopes
    )
    api_url = f"/{kind}/{share_with.name}/shared/{user.name}/"

    fetch_share = partial(api_request, app, api_url, name=requester.name)
    r = await fetch_share()
    assert r.status_code == get_status
    if get_status < 300:
        # check content
        pass

    r = await fetch_share(method="delete")
    assert r.status_code == delete_status
    if delete_status < 300:
        assert r.text == ""
    else:
        # manual delete
        db.delete(share)
        db.commit()

    # now share doesn't exist, should 404
    assert orm.Share.find(db, spawner=spawner, share_with=share_with) is None

    r = await fetch_share()
    assert r.status_code == 404 if get_status < 300 else get_status
    r = await fetch_share(method="delete")
    assert r.status_code == 404 if delete_status < 300 else delete_status


@pytest.mark.parametrize(
    "kind, have_scopes, get_status, delete_status",
    [
        ("users", "read:users:shares!user=SHARE_WITH", 404, 403),
        ("users", "users:shares!user=SHARE_WITH", 404, 404),
        ("users", "users:shares!user=other", 404, 404),
        ("groups", "read:groups:shares!group=SHARE_WITH", 404, 403),
        ("groups", "groups:shares!group=SHARE_WITH", 404, 404),
        ("groups", "groups:shares!group=other", 404, 404),
    ],
)
async def test_single_shared_api_no_such_owner(
    app,
    user,
    share_user,
    group,
    create_user_with_scopes,
    kind,
    have_scopes,
    get_status,
    delete_status,
):
    db = app.db
    share_user.groups.append(group)
    db.commit()
    spawner = user.spawner.orm_spawner  # noqa

    if kind == "users":
        share_with = share_user
    else:
        share_with = group

    owner_name = "nosuchname"

    _expand_scopes = partial(expand_scopes, user=owner_name, share_with=share_with)

    requester = create_user_with_scopes(*_expand_scopes(have_scopes))

    api_url = f"/{kind}/{share_with.name}/shared/{owner_name}/"

    fetch_share = partial(api_request, app, api_url, name=requester.name)
    r = await fetch_share()
    assert r.status_code == get_status

    r = await fetch_share(method="delete")
    assert r.status_code == delete_status


@pytest.mark.parametrize(
    "kind",
    [
        ("users"),
        ("groups"),
    ],
)
async def test_single_shared_api_no_such_target(
    app, user, share_user, group, create_user_with_scopes, kind
):
    db = app.db
    share_user.groups.append(group)
    db.commit()
    spawner = user.spawner.orm_spawner  # noqa
    share_with = "nosuch" + kind

    requester = create_user_with_scopes(f"{kind}:shares")

    api_url = f"/{kind}/{share_with}/shared/{user.name}/"

    fetch_share = partial(api_request, app, api_url, name=requester.name)
    r = await fetch_share()
    assert r.status_code == 404

    r = await fetch_share(method="delete")
    assert r.status_code == 404


@pytest.mark.parametrize(
    "have_scopes, n_groups, n_users, ok",
    [
        ("shares", 0, 0, True),
        ("read:shares", 0, 2, True),
        ("read:shares!user=USER", 3, 0, True),
        ("read:shares!server=SERVER", 2, 1, True),
        ("read:users:shares", 0, 0, False),
    ],
)
async def test_shares_api_list_server(
    app, user, share_user, create_user_with_scopes, have_scopes, n_groups, n_users, ok
):
    db = app.db
    spawner = user.spawner.orm_spawner

    _expand_scopes = partial(expand_scopes, user=user, share_with=share_user)

    requester = create_user_with_scopes(*_expand_scopes(have_scopes))

    expected_shares = []
    for i in range(n_users):
        u = create_user_with_scopes().orm_user
        orm.Share.grant(db, spawner, u)
        expected_shares.append(f"user:{u.name}")

    for i in range(n_groups):
        group = orm.Group(name=new_group_name())
        db.add(group)
        db.commit()
        orm.Share.grant(db, spawner, group)
        expected_shares.append(f"group:{group.name}")
    expected_shares = sorted(expected_shares)
    r = await api_request(app, f"/shares/{user.name}/", name=requester.name)
    if ok:
        assert r.status_code == 200
    else:
        assert r.status_code == 403
        return
    shares = r.json()
    found_shares = []
    for share in shares["items"]:
        assert share["user"] or share["group"]
        if share["user"]:
            found_shares.append(f"user:{share['user']['name']}")
        elif share["group"]:
            found_shares.append(f"group:{share['group']['name']}")
    found_shares = sorted(found_shares)
    assert found_shares == expected_shares


@pytest.mark.parametrize(
    "have_scopes, n_groups, n_users, status",
    [
        ("shares", 0, 0, 200),
        ("read:shares", 0, 2, 200),
        ("read:shares!user=USER", 3, 0, 200),
        ("read:shares!user=other", 3, 0, 404),
        ("read:shares!server=SERVER", 2, 1, 404),
        ("read:users:shares", 0, 0, 403),
    ],
)
async def test_shares_api_list_user(
    app,
    user,
    share_user,
    create_user_with_scopes,
    have_scopes,
    n_groups,
    n_users,
    status,
):
    db = app.db
    spawner = user.spawner.orm_spawner

    _expand_scopes = partial(expand_scopes, user=user, share_with=share_user)

    requester = create_user_with_scopes(*_expand_scopes(have_scopes))

    expected_shares = []
    for i in range(n_users):
        u = create_user_with_scopes().orm_user
        orm.Share.grant(db, spawner, u)
        expected_shares.append(f"user:{u.name}")

    for i in range(n_groups):
        group = orm.Group(name=new_group_name())
        db.add(group)
        db.commit()
        orm.Share.grant(db, spawner, group)
        expected_shares.append(f"group:{group.name}")
    expected_shares = sorted(expected_shares)
    r = await api_request(app, f"/shares/{user.name}", name=requester.name)
    assert r.status_code == status
    if status >= 400:
        return
    shares = r.json()
    found_shares = []
    for share in shares["items"]:
        assert share["user"] or share["group"]
        if share["user"]:
            found_shares.append(f"user:{share['user']['name']}")
        elif share["group"]:
            found_shares.append(f"group:{share['group']['name']}")
    found_shares = sorted(found_shares)
    assert found_shares == expected_shares


async def test_shares_api_list_no_such_owner(app):
    r = await api_request(app, "/shares/nosuchuser")
    assert r.status_code == 404
    r = await api_request(app, "/shares/nosuchuser/")
    assert r.status_code == 404
    r = await api_request(app, "/shares/nosuchuser/namedserver")
    assert r.status_code == 404


@pytest.mark.parametrize(
    "method",
    [
        "post",
        "patch",
        "delete",
    ],
)
async def test_share_api_server_required(app, user, method):
    """test methods defined on /shares/:user/:server not defined on /shares/:user"""
    r = await api_request(app, f"/shares/{user.name}", method=method)
    assert r.status_code == 405


async def test_share_flow_full(
    app, full_spawn, user, share_user, create_user_with_scopes
):
    """Exercise the full process of sharing and then accessing a shared server"""
    user = create_user_with_scopes(
        "shares!user", "self", f"read:users:name!user={share_user.name}"
    )
    # start server
    await user.spawn("")
    await app.proxy.add_user(user)
    spawner = user.spawner

    # grant access
    share_url = f"shares/{user.name}/{spawner.name}"
    r = await api_request(
        app,
        share_url,
        method="post",
        name=user.name,
        data=json.dumps({"user": share_user.name}),
    )
    r.raise_for_status()
    share_model = r.json()

    # attempt to _use_ access
    user_url = public_url(app, user) + "api/contents/"
    token = share_user.new_api_token()
    r = await async_requests.get(user_url, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()

    # revoke access
    r = await api_request(
        app,
        share_url,
        method="patch",
        name=user.name,
        data=json.dumps(
            {
                "scopes": share_model["scopes"],
                "user": share_user.name,
            }
        ),
    )
    r.raise_for_status()
    # new request with new token to avoid cache
    token = share_user.new_api_token()
    r = await async_requests.get(user_url, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


# share codes


@pytest.mark.parametrize(
    "method",
    [
        "post",
        "delete",
    ],
)
async def test_share_codes_api_server_required(app, user, method):
    """test methods defined on /share-codes/:user/:server not defined on /share-codes/:user"""
    r = await api_request(app, f"/share-codes/{user.name}", method=method)
    assert r.status_code == 405


@pytest.mark.parametrize(
    "have_scopes, n_codes, level, status",
    [
        ("shares", 0, 'user', 200),
        ("read:shares", 2, 'server', 200),
        ("read:shares!user=USER", 3, 'user', 200),
        ("read:shares!server=SERVER", 2, 'server', 200),
        ("read:shares!server=SERVER", 2, 'user', 404),
        ("read:users:shares", 0, 'user', 403),
        ("users:shares", 1, 'server', 403),
    ],
)
async def test_share_codes_api_list(
    app, user, share_user, create_user_with_scopes, have_scopes, n_codes, level, status
):
    db = app.db
    spawner = user.spawner.orm_spawner

    _expand_scopes = partial(expand_scopes, user=user, share_with=share_user)
    requester = create_user_with_scopes(*_expand_scopes(have_scopes))

    expected_shares = []
    for i in range(n_codes):
        code = orm.ShareCode(
            spawner=spawner,
            owner=spawner.user,
            scopes=sorted(scopes.access_scopes(spawner=spawner)),
        )
        db.add(code)
        db.commit()
        expected_shares.append(f"sc_{code.id}")

    expected_shares = sorted(expected_shares)
    if level == 'user':
        path = f"/share-codes/{user.name}"
    else:
        path = f"/share-codes/{user.name}/"
    r = await api_request(app, path, name=requester.name)
    assert r.status_code == status
    if status >= 400:
        return
    share_codes = r.json()
    found_shares = []
    for share_code in share_codes["items"]:
        assert 'code' not in share_code
        assert 'id' in share_code
        assert 'server' in share_code
        found_shares.append(share_code["id"])
    found_shares = sorted(found_shares)
    assert found_shares == expected_shares


async def test_share_codes_api_list_no_such_owner(app, user):
    spawner = user.spawner.orm_spawner  # noqa
    r = await api_request(app, "/share-codes/nosuchuser")
    assert r.status_code == 404
    r = await api_request(app, "/share-codes/nosuchuser/")
    assert r.status_code == 404
    r = await api_request(app, f"/share-codes/{user.name}/nosuchserver")
    assert r.status_code == 404


@pytest.mark.parametrize(
    "have_scopes, share_scopes, status",
    [
        (None, None, 200),
        ("shares", None, 200),
        ("shares!user=other", None, 404),
        (
            "shares!server=SERVER,servers!server=SERVER",
            "read:servers!server=SERVER,access:servers!server=SERVER",
            200,
        ),
        (None, "read:servers!server=other/", 400),
        (
            "shares,access:servers",
            "admin:servers!server=SERVER",
            403,
        ),
        (None, None, 200),
    ],
)
async def test_share_codes_api_create(
    app,
    user,
    group,
    share_user,
    create_user_with_scopes,
    have_scopes,
    share_scopes,
    status,
):
    # make sure default spawner exists
    spawner = user.spawner  # noqa
    body = {}
    share_with = share_user
    _expand_scopes = partial(expand_scopes, user=user, share_with=share_with)

    expected_scopes = _expand_scopes("access:servers!server=SERVER")
    if share_scopes:
        share_scopes = _expand_scopes(share_scopes)
        expected_scopes.extend(share_scopes)
        body["scopes"] = share_scopes

    expected_scopes = sorted(set(expected_scopes))

    if have_scopes is None:
        # default: needed permissions
        have_scopes = "shares"

    requester = create_user_with_scopes(*_expand_scopes(have_scopes))

    r = await api_request(
        app,
        f"/share-codes/{user.name}/",
        method="post",
        data=json.dumps(body),
        name=requester.name,
    )
    assert r.status_code == status
    if r.status_code >= 400:
        return

    share_model = r.json()
    assert "scopes" in share_model
    assert sorted(share_model["scopes"]) == expected_scopes
    assert "code" in share_model
    assert "accept_url" in share_model
    parsed_accept_url = urlparse(share_model["accept_url"])
    accept_query = parse_qs(parsed_accept_url.query)
    assert accept_query == {"code": [share_model["code"]]}
    assert parsed_accept_url.path == url_path_join(app.base_url, "hub/accept-share")


@pytest.mark.parametrize(
    "expires_in, status",
    [
        (None, 200),
        ("notanumber", 400),
        (-1, 400),
        (60, 200),
        (525600 * 59, 200),
        (525600 * 60 + 1, 400),
    ],
)
async def test_share_codes_api_create_expires_in(
    app,
    user,
    group,
    create_user_with_scopes,
    expires_in,
    status,
):
    # make sure default spawner exists
    spawner = user.spawner  # noqa
    body = {}
    now = utcnow()
    if expires_in:
        body["expires_in"] = expires_in

    r = await api_request(
        app,
        f"/share-codes/{user.name}/",
        method="post",
        data=json.dumps(body),
    )
    assert r.status_code == status
    if r.status_code >= 400:
        return

    share_model = r.json()
    assert "expires_at" in share_model
    assert share_model["expires_at"]
    expires_at = parse_date(share_model["expires_at"])

    expected_expires_at = now + timedelta(
        seconds=expires_in or orm.ShareCode.default_expires_in
    )
    window = timedelta(seconds=60)
    assert expected_expires_at - window <= expires_at <= expected_expires_at + window

    async def get_code():
        r = await api_request(
            app,
            f"/share-codes/{user.name}/",
        )
        r.raise_for_status()
        codes = r.json()["items"]
        assert len(codes) <= 1
        if len(codes) == 1:
            return codes[0]
        else:
            return None

    code = await get_code()
    assert code

    with mock.patch(
        'jupyterhub.orm.ShareCode.now',
        staticmethod(lambda: (expires_at + timedelta(seconds=1)).replace(tzinfo=None)),
    ):
        code = await get_code()
        assert code is None


@pytest.mark.parametrize(
    "have_scopes, delete_by, status",
    [
        (None, None, 204),
        ("shares", "id=ID", 204),
        (
            "shares!server=SERVER",
            "code=CODE",
            204,
        ),
        ("shares!user=other", None, 404),
        ("read:shares", "code=CODE", 403),
        ("shares", "id=invalid", 404),
        ("shares", "id=sc_9999", 404),
        ("shares", "code=nomatch", 404),
    ],
)
async def test_share_codes_api_revoke(
    app,
    user,
    group,
    share_user,
    create_user_with_scopes,
    have_scopes,
    delete_by,
    status,
):
    db = app.db
    spawner = user.spawner.orm_spawner

    _expand_scopes = partial(expand_scopes, user=user, share_with=share_user)
    # make sure default spawner exists
    spawner = user.spawner.orm_spawner
    share_code, code = orm.ShareCode.new(
        db, spawner, scopes=list(scopes.access_scopes(spawner=spawner))
    )

    assert orm.ShareCode.find(db, code=code)
    other_share_code, other_code = orm.ShareCode.new(
        db, spawner, scopes=list(scopes.access_scopes(spawner=spawner))
    )

    if have_scopes is None:
        # default: needed permissions
        have_scopes = "shares"

    requester = create_user_with_scopes(*_expand_scopes(have_scopes))

    url = f"/share-codes/{user.name}/"
    if delete_by:
        query = delete_by.replace("CODE", code).replace("ID", f"sc_{share_code.id}")
        url = f"{url}?{query}"

    r = await api_request(
        app,
        url,
        method="delete",
        name=requester.name,
    )
    assert r.status_code == status

    # other code unaffected
    if r.status_code >= 400:
        assert orm.ShareCode.find(db, code=code)
        return
    # code has been deleted
    assert orm.ShareCode.find(db, code=code) is None
    if delete_by is None:
        assert orm.ShareCode.find(db, code=other_code) is None
    else:
        assert orm.ShareCode.find(db, code=other_code)


@pytest.mark.parametrize(
    "who, code_arg, get_status, post_status",
    [
        ("share", None, 400, 400),
        ("share", "nosuchcode", 404, 400),
        ("share", "CODE", 200, 302),
        ("self", "CODE", 403, 400),
    ],
)
async def test_accept_share_page(
    app, user, share_user, who, code_arg, get_status, post_status
):
    db = app.db
    spawner = user.spawner.orm_spawner
    orm_code, code = orm.ShareCode.new(
        db, spawner, scopes=list(scopes.access_scopes(spawner=spawner))
    )
    if who == "self":
        cookies = await app.login_user(user.name)
    else:
        cookies = await app.login_user(share_user.name)

    url = "accept-share"
    form_data = {"_xsrf": cookies['_xsrf']}
    if code_arg:
        code_arg = code_arg.replace("CODE", code)
        form_data["code"] = code_arg
        url = url + f"?code={code_arg}"

    r = await get_page(url, app, cookies=cookies)
    assert r.status_code == get_status

    # try submitting the form with the same inputs
    accept_url = public_url(app) + "hub/accept-share"
    r = await async_requests.post(
        accept_url,
        cookies=cookies,
        data=form_data,
        allow_redirects=False,
    )
    assert r.status_code == post_status
    if post_status < 400:
        assert orm_code.exchange_count == 1
        # share is accepted
        assert len(share_user.shared_with_me) == 1
        assert share_user.shared_with_me[0].spawner is spawner
    else:
        assert orm_code.exchange_count == 0
        assert not share_user.shared_with_me


@pytest.mark.parametrize(
    "running, next_url, expected_next",
    [
        (False, None, "{USER_URL}"),
        (True, None, "{USER_URL}"),
        (False, "https://example.com{BASE_URL}", "{USER_URL}"),
        (False, "{BASE_URL}hub", ""),
        (True, "{USER_URL}lab/tree/notebook.ipynb?param=5", ""),
        (False, "{USER_URL}lab/tree/notebook.ipynb?param=5", ""),
    ],
)
async def test_accept_share_page_next_url(
    app,
    user,
    share_user,
    running,
    next_url,
    expected_next,
):
    db = app.db
    spawner = user.spawner.orm_spawner
    orm_code, code = orm.ShareCode.new(
        db, spawner, scopes=list(scopes.access_scopes(spawner=spawner))
    )
    cookies = await app.login_user(share_user.name)

    if running:
        await user.spawn()
        await user.spawner.server.wait_up(http=True)
        await app.proxy.add_user(user)
    else:
        pass

    def expand_url(url):
        url = url.format(
            USER=user.name,
            USER_URL=user.server_url(""),
            BASE_URL=app.base_url,
        )
        return url

    if next_url:
        next_url = expand_url(next_url)
    if expected_next:
        expected_next = expand_url(expected_next)
    else:
        # empty: expect match
        expected_next = next_url

    url = f"accept-share?code={code}"
    form_data = {"_xsrf": cookies['_xsrf']}
    if next_url:
        url = url_concat(url, {"next": next_url})

    r = await get_page(url, app, cookies=cookies)
    assert r.status_code == 200

    page = BeautifulSoup(r.text)
    page_body = page.find("div", class_="container").get_text()
    if running:
        assert "not currently running" not in page_body
    else:
        assert "not currently running" in page_body

    # try submitting the form with the same inputs
    accept_url = r.url
    r = await async_requests.post(
        accept_url,
        cookies=cookies,
        data=form_data,
        allow_redirects=False,
    )
    assert r.status_code == 302
    target = r.headers["Location"]
    # expect absolute path redirect
    expected_next_target = urlunparse(
        urlparse(expected_next)._replace(scheme="", netloc="")
    )
    assert target == expected_next_target
    # is it worth following the redirect?
