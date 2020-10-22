"""Tests for Eventlogging in JupyterHub.

To test a new schema or event, simply add it to the
`valid_events` and `invalid_events` variables below.

You *shouldn't* need to write new tests.
"""
import io
import json
import logging
from unittest import mock

import jsonschema
import pytest
from traitlets.config import Config

from .. import orm
from .mocking import MockHub
from .utils import add_user
from .utils import api_request
from jupyterhub.utils import eventlogging_schema_fqn


def remove_event_capsule(data):
    return {
        k: v for k, v in data.items() if not (k.startswith('__') and k.endswith('__'))
    }


# To test new schemas, add them to the `valid_events`
# and `invalid_events` dictionary below.

# To test valid events, add event item with the form:
# { ( '<schema id>', <version> ) : { <event_data> } }
valid_events = [
    (
        eventlogging_schema_fqn('server-action'),
        1,
        dict(action='start', username='test-username', servername='test-servername'),
    )
]

# To test invalid events, add event item with the form:
# { ( '<schema id>', <version> ) : { <event_data> } }
invalid_events = [
    # Missing required keys
    (eventlogging_schema_fqn('server-action'), 1, dict(action='start'))
]


@pytest.fixture
def eventlog_sink(app):
    """Return eventlog and sink objects"""
    sink = io.StringIO()
    handler = logging.StreamHandler(sink)
    # Update the EventLog config with handler
    cfg = Config()
    cfg.EventLog.handlers = [handler]

    with mock.patch.object(app.config, 'EventLog', cfg.EventLog):
        # recreate the eventlog object with our config
        app.init_eventlog()
        app.tornado_settings['eventlog'] = app.eventlog
        # return the sink from the fixture
        yield app, sink
    # reset eventlog with original config
    app.init_eventlog()


@pytest.mark.parametrize('schema, version, event', valid_events)
def test_valid_events(eventlog_sink, schema, version, event):
    app, sink = eventlog_sink
    eventlog = app.eventlog
    eventlog.allowed_schemas = [schema]
    # Record event
    eventlog.record_event(schema, version, event)
    # Inspect consumed event
    output = sink.getvalue()
    assert output
    data = json.loads(output)
    # Verify event data was recorded
    assert data is not None


@pytest.mark.parametrize('schema, version, event', invalid_events)
def test_invalid_events(eventlog_sink, schema, version, event):
    app, sink = eventlog_sink
    eventlog = app.eventlog
    eventlog.allowed_schemas = [schema]

    # Make sure an error is thrown when bad events are recorded
    with pytest.raises(jsonschema.ValidationError):
        recorded_event = eventlog.record_event(schema, version, event)


async def test_server_event(eventlog_sink):
    schema, version = (eventlogging_schema_fqn('server-action'), 1)

    app, sink = eventlog_sink
    app.eventlog.allowed_schemas = [schema]

    db = app.db
    name = 'user'
    user = add_user(db, app=app, name=name)

    # test user server starting event
    r = await api_request(app, 'users', name, 'server', method='post')
    assert r.status_code == 201
    output = sink.getvalue()
    assert output
    data = remove_event_capsule(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    expected = {'action': 'start', 'username': name, 'servername': ''}
    assert expected.items() <= data.items()

    # test user server stopping event
    r = await api_request(app, 'users', name, 'server', method='delete')
    assert r.status_code == 204
    offset = len(output)
    output = sink.getvalue()[offset:]
    assert output
    data = remove_event_capsule(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    expected = {'action': 'stop', 'username': name, 'servername': ''}
    assert expected.items() <= data.items()


# users to test
# (<username>, <admin>)
users = [('a', True), ('b', False)]


@pytest.mark.parametrize('username, admin', users)
async def test_add_remove_user_event(eventlog_sink, username, admin):
    schema, version = (eventlogging_schema_fqn('user-action'), 1)

    app, sink = eventlog_sink
    app.eventlog.allowed_schemas = [schema]

    user = {'name': username, 'admin': admin}

    r = await api_request(app, 'users', username, method='post', data=json.dumps(user))
    assert r.status_code == 201
    output = sink.getvalue()
    assert output
    data = remove_event_capsule(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    expected = {
        'action': 'create',
        'target_user': {'username': username, 'admin': admin},
        'requester': 'admin',
    }
    assert expected.items() <= data.items()

    r = await api_request(app, 'users', username, method='delete')
    assert r.status_code == 204
    offset = len(output)
    output = sink.getvalue()[offset:]
    assert output
    data = remove_event_capsule(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    expected = {
        'action': 'delete',
        'target_user': {'username': username, 'admin': admin},
        'requester': 'admin',
    }
    assert expected.items() <= data.items()


async def test_add_multi_user_event(eventlog_sink):
    schema, version = (eventlogging_schema_fqn('user-action'), 1)

    app, sink = eventlog_sink
    app.eventlog.allowed_schemas = [schema]

    usernames = [u for u, _ in users]

    r = await api_request(
        app, 'users', method='post', data=json.dumps({'usernames': usernames})
    )
    assert r.status_code == 201

    events = [remove_event_capsule(json.loads(line)) for line in sink.readlines()]

    for event in events:
        jsonschema.validate(event, app.eventlog.schemas[(schema, version)])

    sorted_data = sorted(events, key=lambda x: x['target_user']['username'])

    for username, data in zip(sorted(usernames), sorted_data):
        expected = {
            'action': 'delete',
            'target_user': {'username': username, 'admin': False},
            'requester': 'admin',
        }
        assert expected.items() <= data.items()


async def test_make_admin_event(eventlog_sink):
    schema, version = (eventlogging_schema_fqn('user-action'), 1)

    app, sink = eventlog_sink
    app.eventlog.allowed_schemas = [schema]

    username = 'admin2'
    r = await api_request(app, 'users', username, method='post')
    assert r.status_code == 201
    offset = len(sink.getvalue())

    r = await api_request(
        app, 'users', username, method='patch', data=json.dumps({'admin': True})
    )
    assert r.status_code == 200

    output = sink.getvalue()[offset:]
    assert output
    data = remove_event_capsule(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    expected = {
        'action': 'modify',
        'requester': 'admin',
        'target_user': {'username': username, 'admin': True},
        'prior_state': {'username': username, 'admin': False},
    }
    assert expected.items() <= data.items()
