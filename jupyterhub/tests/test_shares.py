import json
from datetime import timedelta
from unittest import mock

import pytest

from jupyterhub import orm, scopes

from .conftest import new_group_name, new_username
from .utils import add_user, api_request, async_requests, public_url


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


@pytest.mark.parametrize(
    "scopes, have_scopes, allowed",
    [
        (
            "",
            "shares!SERVER,read:users:name",
            True,
        ),
        (
            "",
            "shares!USER,read:users:name!SHARE_WITH",
            True,
        ),
        (
            "",
            "shares",
            False,
        ),
        (
            "",
            "users:shares!USER",
            False,
        ),
        (
            "read:users!USER",
            "shares!SERVER",
            False,
        ),
    ],
)
async def test_share_allowed(
    app, user, share_user, create_user_with_scopes, scopes, have_scopes, allowed
):
    def _expand_scopes(scope_str):
        if not scope_str:
            return []
        return [
            s.replace("USER", f"user={user.name}")
            .replace("SERVER", f"server={user.name}/")
            .replace("SHARE_WITH", f"user={share_user.name}")
            for s in scope_str.split(",")
        ]

    have_scopes = _expand_scopes(have_scopes)
    sharer = create_user_with_scopes(*have_scopes)
    scopes = _expand_scopes(scopes)

    # make sure spawner exists
    user.spawner
    params = {"user": share_user.name}
    if scopes:
        params["scopes"] = scopes

    r = await api_request(
        app,
        f"/shares/{user.name}/",
        method="post",
        data=json.dumps(params),
        name=sharer.name,
    )
    if allowed:
        assert r.status_code == 200
    else:
        assert r.status_code == 403
        return
    got_scopes = r.json()["scopes"]
    # access scope always included
    expected_scopes = sorted(set(scopes) | {f"access:servers!server={user.name}/"})
    assert sorted(got_scopes) == expected_scopes


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

    orm_code.exchange(share_user)
    share_with_scopes = scopes.get_scopes_for(share_user)
    for scope in code_scopes:
        assert scope in share_with_scopes


def test_share_code_expires(app, user):
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

    with mock.patch('jupyterhub.orm.ShareCode.now', lambda: now + timedelta(hours=1)):
        orm.ShareCode.purge_expired(db)
        found = orm.ShareCode.find(db, code=code)
        assert found
        assert found.id == orm_code.id

    with mock.patch('jupyterhub.orm.ShareCode.now', lambda: now + timedelta(hours=25)):
        found = orm.ShareCode.find(db, code=code)
        assert found is None
        orm.ShareCode.purge_expired(db)

    # expired code, should have been deleted
    found = orm.ShareCode.find(db, code=code)
    assert found is None
    assert db.query(orm.ShareCode).filter_by(id=orm_code.id).one_or_none() is None


# API tests


@pytest.mark.parametrize(
    "have_scopes, share_scopes, with_user, with_group, status",
    [
        (None, None, True, False, 400),
        (None, None, False, True, 400),
    ],
)
async def test_share_user_doesnt_exist(
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
    if share_scopes:
        body["scopes"] = share_scopes
    if with_user:
        body["user"] = "nosuchuser"
    if with_group:
        body["group"] = "nosuchgroup"

    r = await api_request(
        app, f"/shares/{user.name}/", method="post", data=json.dumps(body)
    )
    assert r.status_code == status


@pytest.mark.parametrize(
    "have_scopes, share_scopes, with_user, with_group, status",
    [
        (None, None, True, False, 200),
        (None, None, False, True, 200),
        (None, None, False, False, 400),
        (None, None, True, True, 400),
    ],
)
async def test_share_create_api(
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
    if share_scopes:
        body["scopes"] = share_scopes
    if with_user:
        body["user"] = share_user.name
    if with_group:
        body["group"] = group.name

    r = await api_request(
        app, f"/shares/{user.name}/", method="post", data=json.dumps(body)
    )
    assert r.status_code == status
    if r.status_code < 300:
        share_model = r.json()
        assert "scopes" in share_model
        if share_scopes:
            assert share_model["scopes"] == share_scopes


@pytest.mark.parametrize(
    "kind, case",
    [
        ("users", "in-a"),
        ("users", "in-b"),
        ("users", "in-a-b"),
        ("users", "not-in"),
        ("groups", "a"),
        ("groups", "b"),
        ("groups", "c"),
    ],
)
async def test_share_api_list_user_group(
    app, populate_shares, create_user_with_scopes, kind, case
):
    for name, server_names in populate_shares[kind].items():
        if name.rpartition("-")[0] == case:
            break
    else:
        raise ValueError(f"Did not find {case} in {populate_shares[kind].keys()}")

    r = await api_request(app, f"/{kind}/{name}/shared")
    assert r.status_code == 200
    shares = r.json()
    found_shares = sorted(
        [share["server"]["user"]["name"] for share in shares["items"]]
    )
    expected_shares = sorted(server_names)
    assert found_shares == expected_shares


@pytest.mark.parametrize(
    "have_scopes, n_groups, n_users, ok",
    [
        (
            "shares",
            0,
            0,
            True,
        ),
        (
            "read:shares",
            0,
            2,
            True,
        ),
        (
            "read:shares!user=USER",
            3,
            0,
            True,
        ),
        (
            "read:shares!server=SERVER",
            2,
            1,
            True,
        ),
        (
            "read:users:shares",
            0,
            0,
            False,
        ),
    ],
)
async def test_share_api_list_server(
    app, user, share_user, create_user_with_scopes, have_scopes, n_groups, n_users, ok
):
    db = app.db
    spawner = user.spawner.orm_spawner

    def _expand_scopes(scope_str):
        return [
            s.replace("USER", user.name)
            .replace("SERVER", user.name + "/")
            .replace("SHARE_WITH", share_user.name)
            for s in scope_str.split(",")
        ]

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
    # access_scope = scopes.access_scopes(spawner.orm_spawner.oauth_client)

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
    print(f"{user_url=}")
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
    print(r.json())
    assert r.status_code == 403
