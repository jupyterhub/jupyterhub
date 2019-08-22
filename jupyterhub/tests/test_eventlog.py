"""Tests for Eventlogging in JupyterHub. 

To test a new schema or event, simply add it to the 
`valid_events` and `invalid_events` variables below. 

You *shouldn't* need to write new tests.
"""
import io
import json
import logging
import jsonschema
import pytest
from .mocking import MockHub
from traitlets.config import Config


# To test new schemas, add them to the `valid_events`
# and `invalid_events` dictionary below.

# To test valid events, add event item with the form:
# { ( '<schema id>', <version> ) : { <event_data> } }
valid_events = [
    ('hub.jupyter.org/server-action', 1, dict(action='start', username='test-username', servername='test-servername')),
]

# To test invalid events, add event item with the form:
# { ( '<schema id>', <version> ) : { <event_data> } }
invalid_events = [
    # Missing required keys
    ('hub.jupyter.org/server-action', 1, dict(action='start')),
]


@pytest.fixture
def get_hub_and_sink():
    """Get a hub instance with all registered schemas and record an event with it."""
    # Get a mockhub.
    hub = MockHub.instance()
    sink =  io.StringIO()
    handler = logging.StreamHandler(sink)

    def _get_hub_and_sink(schema):
        # Update the hub config with handler info.
        cfg = Config()
        cfg.EventLog.handlers = [handler]
        cfg.EventLog.allowed_schemas = [schema]

        # Get hub app.
        hub.update_config(cfg)
        hub.init_eventlog()

        # Record an event from the hub.
        return hub, sink

    yield _get_hub_and_sink
    
    # teardown
    hub.clear_instance()
    handler.flush()


@pytest.mark.parametrize('schema, version, event', valid_events)
def test_valid_events(get_hub_and_sink, schema, version, event):
    hub, sink = get_hub_and_sink(schema)
    # Record event.
    hub.eventlog.record_event(schema, version, event)
    # Inspect consumed event.
    output = sink.getvalue()
    x = json.loads(output)

    assert x is not None

@pytest.mark.parametrize('schema, version, event', invalid_events)
def test_invalid_events(get_hub_and_sink, schema, version, event):
    hub, sink = get_hub_and_sink(schema)
    
    # Make sure an error is thrown when bad events are recorded.
    with pytest.raises(jsonschema.ValidationError):
        recorded_event = hub.eventlog.record_event(schema, version, event)
