"""Tests for dummy authentication"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import pytest

from jupyterhub.auth import DummyAuthenticator


async def test_dummy_auth_without_global_password():
    authenticator = DummyAuthenticator()
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'test_user', 'password': 'test_pass'}
    )
    assert authorized['name'] == 'test_user'

    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'test_user', 'password': ''}
    )
    assert authorized['name'] == 'test_user'


async def test_dummy_auth_without_username():
    authenticator = DummyAuthenticator()
    authorized = await authenticator.get_authenticated_user(
        None, {'username': '', 'password': 'test_pass'}
    )
    assert authorized is None


async def test_dummy_auth_with_global_password():
    authenticator = DummyAuthenticator()
    authenticator.password = "test_password"

    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'test_user', 'password': 'test_password'}
    )
    assert authorized['name'] == 'test_user'

    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'test_user', 'password': 'qwerty'}
    )
    assert authorized is None

    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'some_other_user', 'password': 'test_password'}
    )
    assert authorized['name'] == 'some_other_user'


async def test_dummy_auth_admin_password_validation():
    authenticator = DummyAuthenticator()

    # Validate that password must also be set
    with pytest.raises(
        ValueError,
        match="DummyAuthenticator.password must be set if admin_password is set",
    ):
        authenticator.admin_password = "a" * 32

    # Validate length
    authenticator.password = "password"
    with pytest.raises(
        ValueError,
        match="DummyAuthenticator.admin_password must be at least 32 characters",
    ):
        authenticator.admin_password = "a" * 31

    # Validate that the passwords aren't the same
    authenticator.password = "a" * 32
    with pytest.raises(
        ValueError,
        match="DummyAuthenticator.password and DummyAuthenticator.admin_password can not be the same",
    ):
        authenticator.admin_password = "a" * 32


async def test_dummy_auth_admin_password():
    authenticator = DummyAuthenticator()
    authenticator.password = "pass"
    authenticator.admin_password = "a" * 32

    # Regular user, regular password
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'test_user', 'password': 'pass'}
    )
    assert authorized['name'] == 'test_user'
    assert not authorized['admin']

    # Regular user, admin password
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'test_user', 'password': 'a' * 32}
    )
    assert not authorized

    # Admin user, admin password
    authenticator.admin_users = {"test_user"}
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'test_user', 'password': 'a' * 32}
    )
    assert authorized['name'] == 'test_user'
    assert authorized['admin']

    # Admin user, regular password
    authenticator.admin_users = {"test_user"}
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'test_user', 'password': 'pass'}
    )
    assert authorized['name'] == 'test_user'
    assert not authorized['admin']

    # Regular user, wrong password
    authenticator.admin_users = set()
    authorized = await authenticator.get_authenticated_user(
        None, {'username': 'test_user', 'password': 'blah'}
    )
    assert not authorized
