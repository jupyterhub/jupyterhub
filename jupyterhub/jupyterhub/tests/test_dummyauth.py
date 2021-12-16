"""Tests for dummy authentication"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
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
