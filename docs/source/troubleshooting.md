# Troubleshooting

When troubleshooting, you may see unexpected behaviors or receive an error
message. This section provide links for identifying the cause of the
problem and how to resolve it.

[*Behavior*](#behavior)
- JupyterHub proxy fails to start
- sudospawner fails to run
- What is the default behavior when none of the lists (admin, allowed,
  allowed groups) are set?
- JupyterHub Docker container not accessible at localhost

[*Errors*](#errors)
- 500 error after spawning my single-user server

[*How do I...?*](#how-do-i)
- Use a chained SSL certificate
- Install JupyterHub without a network connection
- I want access to the whole filesystem, but still default users to their home directory
- How do I increase the number of pySpark executors on YARN?
- How do I use JupyterLab's prerelease version with JupyterHub?
- How do I set up JupyterHub for a workshop (when users are not known ahead of time)?
- How do I set up rotating daily logs?
- Toree integration with HDFS rack awareness script
- Where do I find Docker images and Dockerfiles related to JupyterHub?

[*Troubleshooting commands*](#troubleshooting-commands)

## Behavior

### JupyterHub proxy fails to start

If you have tried to start the JupyterHub proxy and it fails to start:

- check if the JupyterHub IP configuration setting is
  ``c.JupyterHub.ip = '*'``; if it is, try ``c.JupyterHub.ip = ''``
- Try starting with ``jupyterhub --ip=0.0.0.0``

**Note**: If this occurs on Ubuntu/Debian, check that the you are using a
recent version of node. Some versions of Ubuntu/Debian come with a version
of node that is very old, and it is necessary to update node.

### sudospawner fails to run

If the sudospawner script is not found in the path, sudospawner will not run.
To avoid this, specify sudospawner's absolute path. For example, start
jupyterhub with:

    jupyterhub --SudoSpawner.sudospawner_path='/absolute/path/to/sudospawner'

or add:

    c.SudoSpawner.sudospawner_path = '/absolute/path/to/sudospawner'

to the config file, `jupyterhub_config.py`.

### What is the default behavior when none of the lists (admin, allowed, allowed groups) are set?

When nothing is given for these lists, there will be no admins, and all users
who can authenticate on the system (i.e. all the unix users on the server with
a password) will be allowed to start a server. The allowed username set lets you limit
this to a particular set of users, and admin_users lets you specify who
among them may use the admin interface (not necessary, unless you need to do
things like inspect other users' servers, or modify the user list at runtime).

### JupyterHub Docker container not accessible at localhost

Even though the command to start your Docker container exposes port 8000 
(`docker run -p 8000:8000 -d --name jupyterhub jupyterhub/jupyterhub jupyterhub`), 
it is possible that the IP address itself is not accessible/visible. As a result 
when you try http://localhost:8000 in your browser, you are unable to connect 
even though the container is running properly. One workaround is to explicitly 
tell Jupyterhub to start at `0.0.0.0` which is visible to everyone. Try this 
command: 
`docker run -p 8000:8000 -d --name jupyterhub jupyterhub/jupyterhub jupyterhub --ip 0.0.0.0 --port 8000`

### How can I kill ports from JupyterHub managed services that have been orphaned?

I started JupyterHub + nbgrader on the same host without containers. When I try to restart JupyterHub + nbgrader with this configuration, errors appear that the service accounts cannot start because the ports are being used.

How can I kill the processes that are using these ports?

Run the following command:

    sudo kill -9 $(sudo lsof -t -i:<service_port>)

Where `<service_port>` is the port used by the nbgrader course service. This configuration is specified in `jupyterhub_config.py`.

### Why am I getting a Spawn failed error message?

After successfully logging in to JupyterHub with a compatible authenticators, I get a 'Spawn failed' error message in the browser. The JupyterHub logs have `jupyterhub KeyError: "getpwnam(): name not found: <my_user_name>`.

This issue occurs when the authenticator requires a local system user to exist. In these cases, you need to use a spawner
that does not require an existing system user account, such as `DockerSpawner` or `KubeSpawner`.

### How can I run JupyterHub with sudo but use my current env vars and virtualenv location?

When launching JupyterHub with `sudo jupyterhub` I get import errors and my environment variables don't work.

When launching services with `sudo ...` the shell won't have the same environment variables or `PATH`s in place. The most direct way to solve this issue is to use the full path to your python environment and add environment variables. For example:

```bash
sudo MY_ENV=abc123 \
  /home/foo/venv/bin/python3 \
  /srv/jupyterhub/jupyterhub
```

### How can I view the logs for JupyterHub or the user's Notebook servers when using the DockerSpawner?

Use `docker logs <container>` where `<container>` is the container name defined within `docker-compose.yml`.  For example, to view the logs of the JupyterHub container use:

    docker logs hub

By default, the user's notebook server is named `jupyter-<username>` where `username` is the user's username within JupyterHub's db. So if you wanted to see the logs for user `foo` you would use:

    docker logs jupyter-foo

You can also tail logs to view them in real time using the `-f` option:

    docker logs -f hub

## Errors

### 500 error after spawning my single-user server

You receive a 500 error when accessing the URL `/user/<your_name>/...`.
This is often seen when your single-user server cannot verify your user cookie
with the Hub.

There are two likely reasons for this:

1. The single-user server cannot connect to the Hub's API (networking
   configuration problems)
2. The single-user server cannot *authenticate* its requests (invalid token)

#### Symptoms

The main symptom is a failure to load *any* page served by the single-user
server, met with a 500 error. This is typically the first page at `/user/<your_name>`
after logging in or clicking "Start my server". When a single-user notebook server
receives a request, the notebook server makes an API request to the Hub to
check if the cookie corresponds to the right user. This request is logged.

If everything is working, the response logged will be similar to this:

```
200 GET /hub/api/authorizations/cookie/jupyterhub-token-name/[secret] (@10.0.1.4) 6.10ms
```

You should see a similar 200 message, as above, in the Hub log when you first
visit your single-user notebook server. If you don't see this message in the log, it
may mean that your single-user notebook server isn't connecting to your Hub.

If you see 403 (forbidden) like this, it's likely a token problem:

```
403 GET /hub/api/authorizations/cookie/jupyterhub-token-name/[secret] (@10.0.1.4) 4.14ms
```

Check the logs of the single-user notebook server, which may have more detailed
information on the cause.

#### Causes and resolutions

##### No authorization request

If you make an API request and it is not received by the server, you likely
have a network configuration issue. Often, this happens when the Hub is only
listening on 127.0.0.1 (default) and the single-user servers are not on the
same 'machine' (can be physically remote, or in a docker container or VM). The
fix for this case is to make sure that `c.JupyterHub.hub_ip` is an address
that all single-user servers can connect to, e.g.:

```python
c.JupyterHub.hub_ip = '10.0.0.1'
```

##### 403 GET /hub/api/authorizations/cookie

If you receive a 403 error, the API token for the single-user server is likely
invalid. Commonly, the 403 error is caused by resetting the JupyterHub
database (either removing jupyterhub.sqlite or some other action) while
leaving single-user servers running. This happens most frequently when using
DockerSpawner, because Docker's default behavior is to stop/start containers
which resets the JupyterHub database, rather than destroying and recreating
the container every time. This means that the same API token is used by the
server for its whole life, until the container is rebuilt.

The fix for this Docker case is to remove any Docker containers seeing this
issue (typically all containers created before a certain point in time):

    docker rm -f jupyter-name

After this, when you start your server via JupyterHub, it will build a
new container. If this was the underlying cause of the issue, you should see
your server again.

##### Proxy settings (403 GET)

When your whole JupyterHub sits behind a organization proxy (*not* a reverse proxy like NGINX as part of your setup and *not* the configurable-http-proxy) the environment variables `HTTP_PROXY`, `HTTPS_PROXY`, `http_proxy` and `https_proxy` might be set. This confuses the jupyterhub-singleuser servers: When connecting to the Hub for authorization they connect via the proxy instead of directly connecting to the Hub on localhost. The proxy might deny the request (403 GET). This results in the singleuser server thinking it has a wrong auth token. To circumvent this you should add `<hub_url>,<hub_ip>,localhost,127.0.0.1` to the environment variables `NO_PROXY` and `no_proxy`.

### Launching Jupyter Notebooks to run as an externally managed JupyterHub service with the `jupyterhub-singleuser` command returns a `JUPYTERHUB_API_TOKEN` error

[JupyterHub services](https://jupyterhub.readthedocs.io/en/stable/reference/services.html) allow processes to interact with JupyterHub's REST API. Example use-cases include:

* **Secure Testing**: provide a canonical Jupyter Notebook for testing production data to reduce the number of entry points into production systems.
* **Grading Assignments**: provide access to shared Jupyter Notebooks that may be used for management tasks such grading assignments.
* **Private Dashboards**: share dashboards with certain group members.

If possible, try to run the Jupyter Notebook as an externally managed service with one of the provided [jupyter/docker-stacks](https://github.com/jupyter/docker-stacks).

Standard JupyterHub installations include a [jupyterhub-singleuser](https://github.com/jupyterhub/jupyterhub/blob/9fdab027daa32c9017845572ad9d5ba1722dbc53/setup.py#L116) command which is built from the `jupyterhub.singleuser:main` method. The `jupyterhub-singleuser` command is the default command when JupyterHub launches single-user Jupyter Notebooks. One of the goals of this command is to make sure the version of JupyterHub installed within the Jupyter Notebook coincides with the version of the JupyterHub server itself.

If you launch a Jupyter Notebook with the `jupyterhub-singleuser` command directly from the command line the Jupyter Notebook won't have access to the `JUPYTERHUB_API_TOKEN` and will return:

```
    JUPYTERHUB_API_TOKEN env is required to run jupyterhub-singleuser.
    Did you launch it manually?
```

If you plan on testing `jupyterhub-singleuser` independently from JupyterHub, then you can set the api token environment variable. For example, if were to run the single-user Jupyter Notebook on the host, then:

    export JUPYTERHUB_API_TOKEN=my_secret_token
    jupyterhub-singleuser

With a docker container, pass in the environment variable with the run command:

    docker run -d \
      -p 8888:8888 \
      -e JUPYTERHUB_API_TOKEN=my_secret_token \
      jupyter/datascience-notebook:latest

[This example](https://github.com/jupyterhub/jupyterhub/tree/master/examples/service-notebook/external) demonstrates how to combine the use of the `jupyterhub-singleuser` environment variables when launching a Notebook as an externally managed service.

## How do I...?

### Use a chained SSL certificate

Some certificate providers, i.e. Entrust, may provide you with a chained
certificate that contains multiple files. If you are using a chained
certificate you will need to concatenate the individual files by appending the
chain cert and root cert to your host cert:

    cat your_host.crt chain.crt root.crt > your_host-chained.crt

You would then set in your `jupyterhub_config.py` file the `ssl_key` and
`ssl_cert` as follows:

    c.JupyterHub.ssl_cert = your_host-chained.crt
    c.JupyterHub.ssl_key = your_host.key


#### Example

Your certificate provider gives you the following files: `example_host.crt`,
`Entrust_L1Kroot.txt` and `Entrust_Root.txt`.

Concatenate the files appending the chain cert and root cert to your host cert:

    cat example_host.crt Entrust_L1Kroot.txt Entrust_Root.txt > example_host-chained.crt

You would then use the `example_host-chained.crt` as the value for
JupyterHub's `ssl_cert`. You may pass this value as a command line option
when starting JupyterHub or more conveniently set the `ssl_cert` variable in
JupyterHub's configuration file, `jupyterhub_config.py`. In `jupyterhub_config.py`,
set:

    c.JupyterHub.ssl_cert = /path/to/example_host-chained.crt
    c.JupyterHub.ssl_key = /path/to/example_host.key

where `ssl_cert` is example-chained.crt and ssl_key to your private key.

Then restart JupyterHub.

See also [JupyterHub SSL encryption](./getting-started/security-basics.html#ssl-encryption).

### Install JupyterHub without a network connection

Both conda and pip can be used without a network connection. You can make your
own repository (directory) of conda packages and/or wheels, and then install
from there instead of the internet.

For instance, you can install JupyterHub with pip and configurable-http-proxy
with npmbox:

    python3 -m pip wheel jupyterhub
    npmbox configurable-http-proxy

### I want access to the whole filesystem, but still default users to their home directory

Setting the following in `jupyterhub_config.py` will configure access to
the entire filesystem and set the default to the user's home directory.

    c.Spawner.notebook_dir = '/'
    c.Spawner.default_url = '/home/%U' # %U will be replaced with the username

### How do I increase the number of pySpark executors on YARN?

From the command line, pySpark executors can be configured using a command
similar to this one:

    pyspark --total-executor-cores 2 --executor-memory 1G

[Cloudera documentation for configuring spark on YARN applications](https://www.cloudera.com/documentation/enterprise/latest/topics/cdh_ig_running_spark_on_yarn.html#spark_on_yarn_config_apps)
provides additional information. The [pySpark configuration documentation](https://spark.apache.org/docs/0.9.0/configuration.html)
is also helpful for programmatic configuration examples.

### How do I use JupyterLab's prerelease version with JupyterHub?

While JupyterLab is still under active development, we have had users
ask about how to try out JupyterLab with JupyterHub.

You need to install and enable the JupyterLab extension system-wide,
then you can change the default URL to `/lab`.

For instance:

    python3 -m pip install jupyterlab
    jupyter serverextension enable --py jupyterlab --sys-prefix

The important thing is that jupyterlab is installed and enabled in the
single-user notebook server environment. For system users, this means
system-wide, as indicated above. For Docker containers, it means inside
the single-user docker image, etc.

In `jupyterhub_config.py`, configure the Spawner to tell the single-user
notebook servers to default to JupyterLab:

    c.Spawner.default_url = '/lab'

### How do I set up JupyterHub for a workshop (when users are not known ahead of time)?

1. Set up JupyterHub using OAuthenticator for GitHub authentication
2. Configure admin list to have workshop leaders be listed with administrator privileges.

Users will need a GitHub account to login and be authenticated by the Hub.

### How do I set up rotating daily logs?

You can do this with [logrotate](https://linux.die.net/man/8/logrotate),
or pipe to `logger` to use syslog instead of directly to a file.

For example, with this logrotate config file:

```
/var/log/jupyterhub.log {
  copytruncate
  daily
}
```

and run this daily by putting a script in `/etc/cron.daily/`:

```bash
logrotate /path/to/above-config
```

Or use syslog:

    jupyterhub | logger -t jupyterhub

## Troubleshooting commands

The following commands provide additional detail about installed packages,
versions, and system information that may be helpful when troubleshooting
a JupyterHub deployment. The commands are:

- System and deployment information

```bash
jupyter troubleshooting
```

- Kernel information

```bash
jupyter kernelspec list
```

- Debug logs when running JupyterHub

```bash
jupyterhub --debug
```

### Toree integration with HDFS rack awareness script

The Apache Toree kernel will an issue, when running with JupyterHub, if the standard HDFS
rack awareness script is used. This will materialize in the logs as a repeated WARN:

```bash
16/11/29 16:24:20 WARN ScriptBasedMapping: Exception running /etc/hadoop/conf/topology_script.py some.ip.address
ExitCodeException exitCode=1:   File "/etc/hadoop/conf/topology_script.py", line 63
    print rack
             ^
SyntaxError: Missing parentheses in call to 'print'

    at `org.apache.hadoop.util.Shell.runCommand(Shell.java:576)`
```

In order to resolve this issue, there are two potential options.

1. Update HDFS core-site.xml, so the parameter "net.topology.script.file.name" points to a custom
script (e.g. /etc/hadoop/conf/custom_topology_script.py). Copy the original script and change the first line point
to a python two installation (e.g. /usr/bin/python).
2. In spark-env.sh add a Python 2 installation to your path (e.g. export PATH=/opt/anaconda2/bin:$PATH).

### Where do I find Docker images and Dockerfiles related to JupyterHub?

Docker images can be found at the [JupyterHub organization on DockerHub](https://hub.docker.com/u/jupyterhub/).
The Docker image [jupyterhub/singleuser](https://hub.docker.com/r/jupyterhub/singleuser/)
provides an example single user notebook server for use with DockerSpawner.

Additional single user notebook server images can be found at the [Jupyter
organization on DockerHub](https://hub.docker.com/r/jupyter/) and information
about each image at the [jupyter/docker-stacks repo](https://github.com/jupyter/docker-stacks).
