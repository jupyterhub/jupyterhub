import json
import sys
import time
from unittest import mock

from pytest import raises
import requests_mock
from tornado.web import HTTPError

from ..auth import _ExpiringDict, HubAuth
from ...utils import url_path_join

# mock for sending monotonic counter way into the future
monotonic_future = mock.patch('time.monotonic', lambda : sys.maxsize)

def test_expiring_dict():
    cache = _ExpiringDict(max_age=30)
    cache['key'] = 'cached value'
    assert 'key' in cache
    assert cache['key'] == 'cached value'

    with raises(KeyError):
        cache['nokey']

    with monotonic_future:
        assert 'key' not in cache

    cache['key'] = 'cached value'
    assert 'key' in cache
    with monotonic_future:
        assert 'key' not in cache

    cache['key'] = 'cached value'
    assert 'key' in cache
    with monotonic_future:
        with raises(KeyError):
            cache['key']

    cache['key'] = 'cached value'
    assert 'key' in cache
    with monotonic_future:
        assert cache.get('key', 'default') == 'default'
    
    cache.max_age = 0

    cache['key'] = 'cached value'
    assert 'key' in cache
    with monotonic_future:
        assert cache.get('key', 'default') == 'cached value'


def test_hub_auth():
    start = time.monotonic()
    auth = HubAuth(cookie_name='foo')
    mock_model = {
        'name': 'onyxia'
    }
    url = url_path_join(auth.api_url, "authorizations/cookie/foo/bar")
    print(url)
    with requests_mock.Mocker() as m:
        m.get(url, text=json.dumps(mock_model))
        user_model = auth.user_for_cookie('bar')
    assert user_model == mock_model
    # check cache
    user_model = auth.user_for_cookie('bar')
    assert user_model == mock_model
    
    with requests_mock.Mocker() as m:
        m.get(url, status_code=404)
        user_model = auth.user_for_cookie('bar', use_cache=False)
    assert user_model is None
    
    # invalidate cache with timer
    mock_model = {
        'name': 'willow'
    }
    with monotonic_future, requests_mock.Mocker() as m:
        m.get(url, text=json.dumps(mock_model))
        user_model = auth.user_for_cookie('bar')
    assert user_model == mock_model

    with requests_mock.Mocker() as m:
        m.get(url, status_code=500)
        with raises(HTTPError) as exc_info:
            user_model = auth.user_for_cookie('bar', use_cache=False)
    assert exc_info.value.status_code == 502

    with requests_mock.Mocker() as m:
        m.get(url, status_code=400)
        with raises(HTTPError) as exc_info:
            user_model = auth.user_for_cookie('bar', use_cache=False)
    assert exc_info.value.status_code == 500


