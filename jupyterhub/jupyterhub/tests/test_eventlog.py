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

from .mocking import MockHub


# To test new schemas, add them to the `valid_events`
# and `invalid_events` dictionary below.

# To test valid events, add event item with the form:
# { ( '<schema id>', <version> ) : { <event_data> } }
valid_events = [
    (
        'hub.jupyter.org/server-action',
        1,
        dict(action='start', username='test-username', servername='test-servername'),
    )
]

# To test invalid events, add event item with the form:
# { ( '<schema id>', <version> ) : { <event_data> } }
invalid_events = [
    # Missing required keys
    ('hub.jupyter.org/server-action', 1, dict(action='start'))
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
        # return the sink from the fixture
        yield app.eventlog, sink
    # reset eventlog with original config
    app.init_eventlog()


@pytest.mark.parametrize('schema, version, event', valid_events)
def test_valid_events(eventlog_sink, schema, version, event):
    eventlog, sink = eventlog_sink
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
    eventlog, sink = eventlog_sink
    eventlog.allowed_schemas = [schema]

    # Make sure an error is thrown when bad events are recorded
    with pytest.raises(jsonschema.ValidationError):
        recorded_event = eventlog.record_event(schema, version, event)
