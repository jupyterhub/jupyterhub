# Event logging and telemetry

JupyterHub can be configured to record structured events from a running server using Jupyter's [Events System]. The types of events that JupyterHub emits are defined by [JSON schemas] listed at the bottom of this page.

## How to emit events

Event logging is handled by its `EventLogger` object. This leverages Python's standing [logging] library to emit, filter, and collect event data.

To begin recording events, you'll need to set two configurations:

> 1. `handlers`: tells the EventLogger _where_ to route your events. This trait is a list of Python logging handlers that route events to the event log file.
> 2. `allows_schemas`: tells the EventLogger _which_ events should be recorded. No events are emitted by default; all recorded events must be listed here.

Here's a basic example:

```
import logging

c.EventLogger.handlers = [
    logging.FileHandler('event.log'),
]

c.EventLogger.allowed_schemas = [
    'https://schema.jupyter.org/jupyterhub/events/server-action',
]
```

The output is a file, `"event.log"`, with events recorded as JSON data.

(page)=

## Event schemas

```{toctree}
:maxdepth: 2

server-actions
```

:::{versionchanged} 5.0
JupyterHub 5.0 changes from the deprecated jupyter-telemetry to jupyter-events.

The main changes are:

- `EventLog` configuration is now called `EventLogger`
- The `hub.jupyter.org/server-action` schema is now called `https://schema.jupyter.org/jupyterhub/events/server-action`
  :::

[json schemas]: https://json-schema.org/
[logging]: https://docs.python.org/3/library/logging.html
[events system]: https://jupyter-events.readthedocs.io
