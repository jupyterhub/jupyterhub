import json

from .utils import add_user
from .utils import api_request
from jupyterhub import metrics
from jupyterhub import orm


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
