# Writing a custom Spawner

Each single-user server is started by a [Spawner][].
The Spawner represents an abstract interface to a process,
and a custom Spawner needs to be able to take three actions:

1. start the process
2. poll whether the process is still running
3. stop the process

## Spawner.start

`Spawner.start` should start the single-user server for a single user.
Information about the user can be retrieved from `self.user`,
an object encapsulating the user's name, authentication, and server info.

When `Spawner.start` returns, it should have stored the IP and port
of the single-user server in `self.user.server`.

**NOTE:** when writing coroutines, *never* `yield` in between a db change and a commit.
Most `Spawner.start`s should have something looking like:

```python
def start(self):
    self.user.server.ip = 'localhost' # or other host or IP address, as seen by the Hub
    self.user.server.port = 1234 # port selected somehow
    self.db.commit() # always commit before yield, if modifying db values
    yield self._actually_start_server_somehow()
```

When `Spawner.start` returns, the single-user server process should actually be running,
not just requested. JupyterHub can handle `Spawner.start` being very slow
(such as PBS-style batch queues, or instantiating whole AWS instances)
via relaxing the `Spawner.start_timeout` config value.


## Spawner.poll

`Spawner.poll` should check if the spawner is still running.
It should return `None` if it is still running,
and an integer exit status, otherwise.

For the local process case, this uses `os.kill(PID, 0)`
to check if the process is still around.


## Spawner.stop

`Spawner.stop` should stop the process. It must be a tornado coroutine,
and should return when the process has finished exiting.


## Spawner state

JupyterHub should be able to stop and restart without having to teardown
single-user servers. This means that a Spawner may need to persist
some information that it can be restored.
A dictionary of JSON-able state can be used to store this information.

Unlike start/stop/poll, the state methods must not be coroutines.

In the single-process case, this is only the process ID of the server:

```python
def get_state(self):
    """get the current state"""
    state = super().get_state()
    if self.pid:
        state['pid'] = self.pid
    return state

def load_state(self, state):
    """load state from the database"""
    super().load_state(state)
    if 'pid' in state:
        self.pid = state['pid']

def clear_state(self):
    """clear any state (called after shutdown)"""
    super().clear_state()
    self.pid = 0
```



[Spawner]: ../jupyterhub/spawner.py
