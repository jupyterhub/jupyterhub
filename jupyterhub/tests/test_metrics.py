import json
from unittest import mock

import pytest

from .utils import api_request
from .utils import get_page
from jupyterhub import metrics
from jupyterhub import orm
from jupyterhub import roles


async def test_total_users(app):
    num_users = app.db.query(orm.User).count()
    sample = metrics.TOTAL_USERS.collect()[0].samples[0]
    assert sample.value == num_users

    await api_request(
        app, "/users", method="post", data=json.dumps({"usernames": ["incrementor"]})
    )

    sample = metrics.TOTAL_USERS.collect()[0].samples[0]
    assert sample.value == num_users + 1

    # GET /users used to double-count
    await api_request(app, "/users")

    # populate the Users cache dict if any are missing:
    for user in app.db.query(orm.User):
        _ = app.users[user.id]

    sample = metrics.TOTAL_USERS.collect()[0].samples[0]
    assert sample.value == num_users + 1

    await api_request(app, "/users/incrementor", method="delete")

    sample = metrics.TOTAL_USERS.collect()[0].samples[0]
    assert sample.value == num_users


@pytest.mark.parametrize(
    "authenticate_prometheus, authenticated, authorized, success",
    [
        (True, True, True, True),
        (True, True, False, False),
        (True, False, False, False),
        (False, True, True, True),
        (False, False, False, True),
    ],
)
async def test_metrics_auth(
    app,
    authenticate_prometheus,
    authenticated,
    authorized,
    success,
    create_temp_role,
    user,
):
    if authorized:
        role = create_temp_role(["read:metrics"])
        roles.grant_role(app.db, user, role)

    headers = {}
    if authenticated:
        token = user.new_api_token()
        headers["Authorization"] = f"token {token}"

    with mock.patch.dict(
        app.tornado_settings, {"authenticate_prometheus": authenticate_prometheus}
    ):
        r = await get_page("metrics", app, headers=headers)
    if success:
        assert r.status_code == 200
    else:
        assert r.status_code == 403
        assert 'read:metrics' in r.text
