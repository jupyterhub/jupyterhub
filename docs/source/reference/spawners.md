# Spawners

A [Spawner][] starts each single-user notebook server.
The Spawner represents an abstract interface to a process,
and a custom Spawner needs to be able to take three actions:

- start the process
- poll whether the process is still running
- stop the process


## Examples

Custom Spawners for JupyterHub can be found on the [JupyterHub wiki](https://github.com/jupyterhub/jupyterhub/wiki/Spawners).
Some examples include:

- [DockerSpawner](https://github.com/jupyterhub/dockerspawner) for spawning user servers in Docker containers
  * `dockerspawner.DockerSpawner` for spawning identical Docker containers for
    each users
  * `dockerspawner.SystemUserSpawner` for spawning Docker containers with an
    environment and home directory for each users
  * both `DockerSpawner` and `SystemUserSpawner` also work with Docker Swarm for
    launching containers on remote machines
- [SudoSpawner](https://github.com/jupyterhub/sudospawner) enables JupyterHub to
  run without being root, by spawning an intermediate process via `sudo`
- [BatchSpawner](https://github.com/jupyterhub/batchspawner) for spawning remote
  servers using batch systems
- [YarnSpawner](https://github.com/jupyterhub/yarnspawner) for spawning notebook
  servers in YARN containers on a Hadoop cluster
- [SSHSpawner](https://github.com/NERSC/sshspawner) to spawn notebooks
  on a remote server using SSH


## Spawner control methods

### Spawner.start

`Spawner.start` should start the single-user server for a single user.
Information about the user can be retrieved from `self.user`,
an object encapsulating the user's name, authentication, and server info.

The return value of `Spawner.start` should be the (ip, port) of the running server.

**NOTE:** When writing coroutines, *never* `yield` in between a database change and a commit.

Most `Spawner.start` functions will look similar to this example:

```python
def start(self):
    self.ip = '127.0.0.1'
    self.port = random_port()
    # get environment variables,
    # several of which are required for configuring the single-user server
    env = self.get_env()
    cmd = []
    # get jupyterhub command to run,
    # typically ['jupyterhub-singleuser']
    cmd.extend(self.cmd)
    cmd.extend(self.get_args())

    yield self._actually_start_server_somehow(cmd, env)
    return (self.ip, self.port)
```

When `Spawner.start` returns, the single-user server process should actually be running,
not just requested. JupyterHub can handle `Spawner.start` being very slow
(such as PBS-style batch queues, or instantiating whole AWS instances)
via relaxing the `Spawner.start_timeout` config value.

### Spawner.poll

`Spawner.poll` should check if the spawner is still running.
It should return `None` if it is still running,
and an integer exit status, otherwise.

For the local process case, `Spawner.poll` uses `os.kill(PID, 0)`
to check if the local process is still running. On Windows, it uses `psutil.pid_exists`.

### Spawner.stop

`Spawner.stop` should stop the process. It must be a tornado coroutine, which should return when the process has finished exiting.


## Spawner state

JupyterHub should be able to stop and restart without tearing down
single-user notebook servers. To do this task, a Spawner may need to persist
some information that can be restored later.
A JSON-able dictionary of state can be used to store persisted information.

Unlike start, stop, and poll methods, the state methods must not be coroutines.

For the single-process case, the Spawner state is only the process ID of the server:

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


## Spawner options form

(new in 0.4)

Some deployments may want to offer options to users to influence how their servers are started.
This may include cluster-based deployments, where users specify what resources should be available,
or docker-based deployments where users can select from a list of base images.

This feature is enabled by setting `Spawner.options_form`, which is an HTML form snippet
inserted unmodified into the spawn form.
If the `Spawner.options_form` is defined, when a user tries to start their server, they will be directed to a form page, like this:

![spawn-form](../images/spawn-form.png)

If `Spawner.options_form` is undefined, the user's server is spawned directly, and no spawn page is rendered.

See [this example](https://github.com/jupyterhub/jupyterhub/blob/master/examples/spawn-form/jupyterhub_config.py) for a form that allows custom CLI args for the local spawner.

### `Spawner.options_from_form`

Options from this form will always be a dictionary of lists of strings, e.g.:

```python
{
  'integer': ['5'],
  'text': ['some text'],
  'select': ['a', 'b'],
}
```

When `formdata` arrives, it is passed through `Spawner.options_from_form(formdata)`,
which is a method to turn the form data into the correct structure.
This method must return a dictionary, and is meant to interpret the lists-of-strings into the correct types. For example, the `options_from_form` for the above form would look like:

```python
def options_from_form(self, formdata):
    options = {}
    options['integer'] = int(formdata['integer'][0]) # single integer value
    options['text'] = formdata['text'][0] # single string value
    options['select'] = formdata['select'] # list already correct
    options['notinform'] = 'extra info' # not in the form at all
    return options
```

which would return:

```python
{
  'integer': 5,
  'text': 'some text',
  'select': ['a', 'b'],
  'notinform': 'extra info',
}
```

When `Spawner.start` is called, this dictionary is accessible as `self.user_options`.


[Spawner]: https://github.com/jupyterhub/jupyterhub/blob/master/jupyterhub/spawner.py

## Writing a custom spawner

If you are interested in building a custom spawner, you can read [this tutorial](http://jupyterhub-tutorial.readthedocs.io/en/latest/spawners.html).

### Registering custom Spawners via entry points

As of JupyterHub 1.0, custom Spawners can register themselves via
the `jupyterhub.spawners` entry point metadata.
To do this, in your `setup.py` add:

```python
setup(
  ...
  entry_points={
    'jupyterhub.spawners': [
        'myservice = mypackage:MySpawner',
    ],
  },
)
```

If you have added this metadata to your package,
users can select your spawner with the configuration:

```python
c.JupyterHub.spawner_class = 'myservice'
```

instead of the full

```python
c.JupyterHub.spawner_class = 'mypackage:MySpawner'
```

previously required.
Additionally, configurable attributes for your spawner will
appear in jupyterhub help output and auto-generated configuration files
via `jupyterhub --generate-config`.


## Spawners, resource limits, and guarantees (Optional)

Some spawners of the single-user notebook servers allow setting limits or
guarantees on resources, such as CPU and memory. To provide a consistent
experience for sysadmins and users, we provide a standard way to set and
discover these resource limits and guarantees, such as for memory and CPU.
For the limits and guarantees to be useful, **the spawner must implement
support for them**. For example, LocalProcessSpawner, the default
spawner, does not support limits and guarantees. One of the spawners
that supports limits and guarantees is the `systemdspawner`.


### Memory Limits & Guarantees

`c.Spawner.mem_limit`: A **limit** specifies the *maximum amount of memory*
that may be allocated, though there is no promise that the maximum amount will
be available. In supported spawners, you can set `c.Spawner.mem_limit` to
limit the total amount of memory that a single-user notebook server can
allocate. Attempting to use more memory than this limit will cause errors. The
single-user notebook server can discover its own memory limit by looking at
the environment variable `MEM_LIMIT`, which is specified in absolute bytes.

`c.Spawner.mem_guarantee`: Sometimes, a **guarantee** of a *minimum amount of
memory* is desirable. In this case, you can set `c.Spawner.mem_guarantee` to
to provide a guarantee that at minimum this much memory will always be
available for the single-user notebook server to use. The environment variable
`MEM_GUARANTEE` will also be set in the single-user notebook server.

**The spawner's underlying system or cluster is responsible for enforcing these
limits and providing these guarantees.** If these values are set to `None`, no
limits or guarantees are provided, and no environment values are set.

### CPU Limits & Guarantees

`c.Spawner.cpu_limit`: In supported spawners, you can set
`c.Spawner.cpu_limit` to limit the total number of cpu-cores that a
single-user notebook server can use. These can be fractional - `0.5` means 50%
of one CPU core, `4.0` is 4 cpu-cores, etc. This value is also set in the
single-user notebook server's environment variable `CPU_LIMIT`. The limit does
not claim that you will be able to use all the CPU up to your limit as other
higher priority applications might be taking up CPU.

`c.Spawner.cpu_guarantee`: You can set `c.Spawner.cpu_guarantee` to provide a
guarantee for CPU usage. The environment variable `CPU_GUARANTEE` will be set
in the single-user notebook server when a guarantee is being provided.

**The spawner's underlying system or cluster is responsible for enforcing these
limits and providing these guarantees.** If these values are set to `None`, no
limits or guarantees are provided, and no environment values are set.

### Encryption

Communication between the `Proxy`, `Hub`, and `Notebook` can be secured by
turning on `internal_ssl` in `jupyterhub_config.py`. For a custom spawner to
utilize these certs, there are two methods of interest on the base `Spawner`
class: `.create_certs` and `.move_certs`.

The first method, `.create_certs` will sign a key-cert pair using an internally
trusted authority for notebooks.  During this process, `.create_certs` can
apply `ip` and `dns` name information to the cert via an `alt_names` `kwarg`.
This is used for certificate authentication (verification). Without proper
verification, the `Notebook` will be unable to communicate with the `Hub` and
vice versa when `internal_ssl` is enabled. For example, given a deployment
using the `DockerSpawner` which will start containers with `ips` from the
`docker` subnet pool, the `DockerSpawner` would need to instead choose a
container `ip` prior to starting and pass that to `.create_certs` (TODO: edit).

In general though, this method will not need to be changed and the default
`ip`/`dns` (localhost) info will suffice.

When `.create_certs` is run, it will `.create_certs` in a default, central
location specified by `c.JupyterHub.internal_certs_location`. For `Spawners`
that need access to these certs elsewhere (i.e. on another host altogether),
the `.move_certs` method can be overridden to move the certs appropriately.
Again, using `DockerSpawner` as an example, this would entail moving certs
to a directory that will get mounted into the container this spawner starts.
