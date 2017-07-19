## External services

JupyterHub has a REST API that can be used by external services like the
[cull_idle_servers](https://github.com/jupyterhub/jupyterhub/blob/master/examples/cull-idle/cull_idle_servers.py)
script which monitors and kills idle single-user servers periodically. In order to run such an
external service, you need to provide it an API token. In the case of `cull_idle_servers`, it is passed
as the environment variable called `JPY_API_TOKEN`.

Currently there are two ways of registering that token with JupyterHub. The first one is to use
the `jupyterhub` command to generate a token for a specific hub user:

```bash
jupyterhub token <username>
```

As of [version 0.6.0](./changelog.html), the preferred way of doing this is to first generate an API token:

```bash
openssl rand -hex 32
```


and then write it to your JupyterHub configuration file (note that the **key** is the token while the **value** is the username):

```python
c.JupyterHub.api_tokens = {'token' : 'username'}
```

Upon restarting JupyterHub, you should see a message like below in the logs:

```
Adding API token for <username>
```

Now you can run your script, i.e. `cull_idle_servers`, by providing it the API token and it will authenticate through
the REST API to interact with it.
