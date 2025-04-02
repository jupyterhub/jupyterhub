import pytest
from traitlets.config import Config

from jupyterhub.authenticators.shared import SharedPasswordAuthenticator


@pytest.fixture
def admin_password():
    return "a" * 32


@pytest.fixture
def user_password():
    return "user_password"


@pytest.fixture
def authenticator(admin_password, user_password):
    return SharedPasswordAuthenticator(
        admin_password=admin_password,
        user_password=user_password,
        admin_users={"admin"},
        allow_all=True,
    )


async def test_password_validation():
    authenticator = SharedPasswordAuthenticator()
    # Validate length
    with pytest.raises(
        ValueError,
        match="admin_password must be at least 32 characters",
    ):
        authenticator.admin_password = "a" * 31

    with pytest.raises(
        ValueError,
        match="user_password must be at least 8 characters",
    ):
        authenticator.user_password = "a" * 7

    # Validate that the passwords aren't the same
    authenticator.user_password = "a" * 32
    with pytest.raises(
        ValueError,
        match="SharedPasswordAuthenticator.user_password and SharedPasswordAuthenticator.admin_password cannot be the same",
    ):
        authenticator.admin_password = "a" * 32

    # ok
    authenticator.admin_password = "a" * 33

    # check collision in the other order
    with pytest.raises(
        ValueError,
        match="SharedPasswordAuthenticator.user_password and SharedPasswordAuthenticator.admin_password cannot be the same",
    ):
        authenticator.user_password = "a" * 33


async def test_admin_password(authenticator, user_password, admin_password):
    # Regular user, regular password
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'test_user', 'password': user_password}
    )
    assert authorized['name'] == 'test_user'
    assert not authorized['admin']

    # Regular user, admin password
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'test_user', 'password': admin_password}
    )
    assert not authorized

    # Admin user, admin password
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'admin', 'password': admin_password}
    )
    assert authorized['name'] == 'admin'
    assert authorized['admin']

    # Admin user, regular password
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'admin', 'password': user_password}
    )
    assert not authorized

    # Regular user, wrong password
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'test_user', 'password': 'blah'}
    )
    assert not authorized

    # New username, allow_all is False
    authenticator.allow_all = False
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'new_user', 'password': 'user_password'}
    )
    assert not authorized


async def test_empty_passwords():
    authenticator = SharedPasswordAuthenticator(
        allow_all=True,
        admin_users={"admin"},
        user_password="",
        admin_password="",
    )
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'admin', 'password': ''}
    )
    assert not authorized
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'user', 'password': ''}
    )
    assert not authorized


@pytest.mark.parametrize(
    "auth_config, warns, not_warns",
    [
        pytest.param({}, "nobody can login", "", id="default"),
        pytest.param(
            {"allow_all": True},
            "Nobody will be able to login",
            "regular users",
            id="no passwords",
        ),
        pytest.param(
            {"admin_password": "a" * 32}, "admin_users is not", "", id="no admin_users"
        ),
        pytest.param(
            {"admin_users": {"admin"}},
            "admin_password is not",
            "",
            id="no admin_password",
        ),
        pytest.param(
            {"admin_users": {"admin"}, "admin_password": "a" * 32, "allow_all": True},
            "No non-admin users will be able to login",
            "",
            id="only_admin",
        ),
    ],
)
def test_check_allow_config(caplog, auth_config, warns, not_warns):
    # check log warnings
    config = Config()
    for key, value in auth_config.items():
        setattr(config.SharedPasswordAuthenticator, key, value)
    authenticator = SharedPasswordAuthenticator(config=config)
    authenticator.check_allow_config()
    if warns:
        if isinstance(warns, str):
            warns = [warns]
        for snippet in warns:
            assert snippet in caplog.text
    if not_warns:
        if isinstance(not_warns, str):
            not_warns = [not_warns]
        for snippet in not_warns:
            assert snippet not in caplog.text
