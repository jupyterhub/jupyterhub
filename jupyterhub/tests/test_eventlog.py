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
from .utils import find_user
from jupyterhub.utils import eventlogging_schema_fqn


def remove_event_metadata(data):
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


# ----------------------
# Server API event tests
# ----------------------


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
    data = remove_event_metadata(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    expected = {'action': 'start', 'username': name, 'servername': ''}
    assert expected.items() <= data.items()

    # test user server stopping event
    r = await api_request(app, 'users', name, 'server', method='delete')
    assert r.status_code == 204
    offset = len(output)
    output = sink.getvalue()[offset:]
    assert output
    data = remove_event_metadata(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    expected = {'action': 'stop', 'username': name, 'servername': ''}
    assert expected.items() <= data.items()


# --------------------
# User API event tests
# --------------------


# users to test
# (<username>, <admin>)
users = [('a', True), ('b', False)]
usernames = [username for username, _ in users]


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
    data = remove_event_metadata(json.loads(output))
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
    data = remove_event_metadata(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    expected = {
        'action': 'delete',
        'target_user': {'username': username, 'admin': admin},
        'requester': 'admin',
    }
    assert expected.items() <= data.items()


async def test_list_users_event(eventlog_sink):
    schema, version = (eventlogging_schema_fqn('user-action'), 1)

    app, sink = eventlog_sink
    app.eventlog.allowed_schemas = [schema]

    r = await api_request(app, 'users', method='get')
    assert r.status_code == 200

    output = sink.getvalue()
    assert output
    data = remove_event_metadata(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    expected = {'action': 'list', 'requester': 'admin'}
    assert expected.items() <= data.items()


async def test_add_multi_user_event(eventlog_sink):
    schema, version = (eventlogging_schema_fqn('user-action'), 1)

    app, sink = eventlog_sink
    app.eventlog.allowed_schemas = [schema]

    r = await api_request(
        app, 'users', method='post', data=json.dumps({'usernames': usernames})
    )
    assert r.status_code == 201

    sink.seek(0)
    events = [
        remove_event_metadata(json.loads(line)) for line in sink.readlines() if line
    ]

    for event in events:
        jsonschema.validate(event, app.eventlog.schemas[(schema, version)])

    sorted_data = sorted(events, key=lambda x: x['target_user']['username'])

    for username, data in zip(sorted(usernames), sorted_data):
        expected = {
            'action': 'create',
            'target_user': {'username': username, 'admin': False},
            'requester': 'admin',
        }
        assert expected.items() <= data.items()


async def test_make_admin_event(eventlog_sink):
    schema, version = (eventlogging_schema_fqn('user-action'), 1)

    app, sink = eventlog_sink
    app.eventlog.allowed_schemas = [schema]

    username = 'admin2'
    add_user(app.db, name=username)

    r = await api_request(
        app, 'users', username, method='patch', data=json.dumps({'admin': True})
    )
    assert r.status_code == 200

    output = sink.getvalue()
    assert output
    data = remove_event_metadata(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    expected = {
        'action': 'modify',
        'requester': 'admin',
        'target_user': {'username': username, 'admin': True},
        'prior_state': {'username': username, 'admin': False},
    }
    assert expected.items() <= data.items()


# ---------------------
# Group API event tests
# ---------------------


async def test_group_create_event(eventlog_sink):
    schema, version = (eventlogging_schema_fqn('group-action'), 1)

    app, sink = eventlog_sink
    app.eventlog.allowed_schemas = [schema]

    group_name = 'group1'

    r = await api_request(app, 'groups', group_name, method='post')
    assert r.status_code == 201

    output = sink.getvalue()
    assert output
    data = remove_event_metadata(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    expected = {'action': 'create', 'requester': 'admin', 'group': group_name}
    assert expected.items() <= data.items()


async def test_group_list_event(eventlog_sink):
    schema, version = (eventlogging_schema_fqn('group-action'), 1)

    app, sink = eventlog_sink
    app.eventlog.allowed_schemas = [schema]

    r = await api_request(app, 'groups', method='get')
    assert r.status_code == 200

    output = sink.getvalue()
    assert output
    data = remove_event_metadata(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    expected = {'action': 'list', 'requester': 'admin'}
    assert expected.items() <= data.items()


async def test_group_get_event(eventlog_sink):
    schema, version = (eventlogging_schema_fqn('group-action'), 1)

    app, sink = eventlog_sink
    app.eventlog.allowed_schemas = [schema]

    group_name = 'group1'

    r = await api_request(app, 'groups', group_name, method='get')
    assert r.status_code == 200

    output = sink.getvalue()
    assert output
    data = remove_event_metadata(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    expected = {'action': 'get', 'requester': 'admin', 'group': group_name}
    assert expected.items() <= data.items()


async def test_group_add_delete_users_event(eventlog_sink):
    schema, version = (eventlogging_schema_fqn('group-membership-action'), 1)

    app, sink = eventlog_sink
    app.eventlog.allowed_schemas = [schema]

    group_name = 'group1'

    r = await api_request(
        app,
        'groups',
        group_name,
        'users',
        method='post',
        data=json.dumps({'users': usernames}),
    )
    r.raise_for_status()

    output = sink.getvalue()
    assert output
    data = remove_event_metadata(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    data['usernames'].sort()
    expected = {
        'action': 'add',
        'group': group_name,
        'usernames': sorted(usernames),
        'requester': 'admin',
    }
    assert expected.items() <= data.items()

    r = await api_request(
        app,
        'groups',
        group_name,
        'users',
        method='delete',
        data=json.dumps({'users': usernames}),
    )
    r.status_code == 204

    offset = len(output)
    output = sink.getvalue()[offset:]
    assert output
    data = remove_event_metadata(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    data['usernames'].sort()
    expected = {
        'action': 'remove',
        'group': group_name,
        'usernames': sorted(usernames),
        'requester': 'admin',
    }
    assert expected.items() <= data.items()


async def test_group_create_with_users_event(eventlog_sink):
    group_schema, group_version = (eventlogging_schema_fqn('group-action'), 1)
    group_member_schema, group_member_version = (
        eventlogging_schema_fqn('group-membership-action'),
        1,
    )

    app, sink = eventlog_sink
    app.eventlog.allowed_schemas = [group_schema, group_member_schema]

    group_name = 'group2'

    r = await api_request(
        app, 'groups', group_name, method='post', data=json.dumps({'users': usernames})
    )
    assert r.status_code == 201

    sink.seek(0)
    events = [json.loads(line) for line in sink.readlines() if line]
    create_group_event = [
        remove_event_metadata(e) for e in events if e['__schema__'] == group_schema
    ][0]
    jsonschema.validate(
        create_group_event, app.eventlog.schemas[(group_schema, group_version)],
    )
    expected = {
        'action': 'create',
        'group': group_name,
        'requester': 'admin',
    }
    assert expected.items() <= create_group_event.items()

    add_user_event = [
        remove_event_metadata(e)
        for e in events
        if e['__schema__'] == group_member_schema
    ][0]
    jsonschema.validate(
        add_user_event,
        app.eventlog.schemas[(group_member_schema, group_member_version)],
    )
    add_user_event['usernames'].sort()
    expected = {
        'action': 'add',
        'group': group_name,
        'usernames': sorted(usernames),
        'requester': 'admin',
    }
    assert expected.items() <= add_user_event.items()


async def test_group_delete_event(eventlog_sink):
    schema, version = (eventlogging_schema_fqn('group-action'), 1)

    app, sink = eventlog_sink
    app.eventlog.allowed_schemas = [schema]

    group_names = ['group1', 'group2']

    offset = 0
    for group_name in group_names:
        r = await api_request(app, 'groups', group_name, method='delete',)
        assert r.status_code == 204

        output = sink.getvalue()[offset:]
        offset += len(output)
        assert output
        data = remove_event_metadata(json.loads(output))
        jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
        expected = {
            'action': 'delete',
            'group': group_name,
            'requester': 'admin',
        }
        assert expected.items() <= data.items()


# ---------------------
# Token API event tests
# ---------------------


async def test_token_event(eventlog_sink):
    schema, version = (eventlogging_schema_fqn('token-action'), 1)

    app, sink = eventlog_sink
    app.eventlog.allowed_schemas = [schema]

    username = 'admin'

    r = await api_request(app, 'users', username, 'tokens', method='post')
    assert r.status_code == 200

    reply = r.json()
    token_id = reply['id']

    offset = 0
    output = sink.getvalue()[offset:]
    assert output
    data = remove_event_metadata(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    expected = {'action': 'create', 'target_user': username, 'requester': username}
    assert expected.items() <= data.items()

    r = await api_request(app, 'users', username, 'tokens', method='get')
    assert r.status_code == 200
    offset += len(output)
    output = sink.getvalue()[offset:]
    assert output
    data = remove_event_metadata(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    expected = {'action': 'list', 'target_user': username, 'requester': username}
    assert expected.items() <= data.items()

    r = await api_request(app, 'users', username, 'tokens', token_id, method='get')
    assert r.status_code == 200
    offset += len(output)
    output = sink.getvalue()[offset:]
    assert output
    data = remove_event_metadata(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    expected = {
        'action': 'get',
        'target_user': username,
        'requester': username,
        'token_id': token_id,
    }
    assert expected.items() <= data.items()

    r = await api_request(app, 'users', username, 'tokens', token_id, method='delete')
    assert r.status_code == 204
    offset += len(output)
    output = sink.getvalue()[offset:]
    assert output
    data = remove_event_metadata(json.loads(output))
    jsonschema.validate(data, app.eventlog.schemas[(schema, version)])
    expected = {
        'action': 'delete',
        'target_user': username,
        'requester': username,
        'token_id': token_id,
    }
    assert expected.items() <= data.items()
