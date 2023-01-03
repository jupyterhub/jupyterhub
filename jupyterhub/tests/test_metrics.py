import json
from datetime import timedelta
from unittest import mock

import pytest

from jupyterhub import metrics, orm, roles

from ..utils import utcnow
from .utils import add_user, api_request, get_page


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


async def test_active_users(app):
    db = app.db
    collector = metrics.PeriodicMetricsCollector(db=db)
    collector.update_active_users()
    now = utcnow()

    def collect():
        samples = metrics.ACTIVE_USERS.collect()[0].samples
        by_period = {
            metrics.ActiveUserPeriods(sample.labels["period"]): sample.value
            for sample in samples
        }
        print(by_period)
        return by_period

    baseline = collect()

    for i, offset in enumerate(
        [
            None,
            # in 24h
            timedelta(hours=23, minutes=30),
            # in 7d
            timedelta(hours=24, minutes=1),
            timedelta(days=6, hours=23, minutes=30),
            # in 30d
            timedelta(days=7, minutes=1),
            timedelta(days=29, hours=23, minutes=30),
            # not in any
            timedelta(days=30, minutes=1),
        ]
    ):
        user = add_user(db, name=f"active-{i}")
        if offset:
            user.last_activity = now - offset
        else:
            user.last_activity = None
        db.commit()

    # collect before update is called, don't include new users
    counts = collect()
    for period in metrics.ActiveUserPeriods:
        assert period in counts
        assert counts[period] == baseline[period]

    # collect after updates, check updated counts
    collector.update_active_users()
    counts = collect()
    assert (
        counts[metrics.ActiveUserPeriods.twenty_four_hours]
        == baseline[metrics.ActiveUserPeriods.twenty_four_hours] + 1
    )
    assert (
        counts[metrics.ActiveUserPeriods.seven_days]
        == baseline[metrics.ActiveUserPeriods.seven_days] + 3
    )
    assert (
        counts[metrics.ActiveUserPeriods.thirty_days]
        == baseline[metrics.ActiveUserPeriods.thirty_days] + 5
    )
