# What is Jupyter and JupyterHub?

JupyterHub is not what you think it is.  Most things you think are
part of JupyterHub are actually handled by some other component, and
it's not always obvious how the parts relate.  This document was
originally written to assist in debugging: very often, the actual
problem is not where one thinks it is and thus people can't easily
debug.  In order to tell this story, we start at JupyterHub and go all
the way down to the fundamental components of Jupyter.

We occasionally leave things out or bend the truth where it helps in
explanation, and give our explanations in terms of Python even though
many other languages can be used instead.

This guide is long, but after reading it you will be know of all major
components in the Jupyter ecosystem and everything else you read
should make sense.



## Just what is Jupyter?

Before we get too far, let's remember what our end goal is.  A Jupyter
Notebook is really nothing more than a Python process (or some
language) which is getting commands from a web browser and displaying
the output via a browser.  What the process actually sees can roughly
be considered getting data on standard input and writing to standard
output (*).  There is nothing intrinsically special about this process
- it can do anything a normal Python process can do, and nothing more.
The kernel handles capturing output and converting things like
graphics to a form usable by the browser.

Everything we explain below is building up to this, going through many
different layers which give you many ways of customizing how this
process runs.  But this process is not *too* special.



## JupyterHub

**JupyterHub** is the central piece that provides multi-user
login. Despite this, the end user only briefly interacts with it and
most of the actual Jupyter session does not relate to the hub at all.
In short, anything which is related to *starting* the user's workspace
is about JupyterHub, anything about *running* usually isn't.

If you have problems connecting the authentication, spawning, and the
proxy (explained below), the issues is usually with JupyterHub.  To
debug, JupyterHub has extensive logs which get printed to its console
and can be used to discover most problems.

JupyterHub consists of the main pieces below:

### Authenticators

JupyterHub itself doesn't actually (necessarily) manage your users.
It has a database of users, but it is usually connected with some
other system that manages the usernames and passwords.  When someone
tries to log in to JupyteHub, it just asks the **authenticator** if
the username/password is valid.  The authenticator can also return
user groups and admin status of users, so that JupyterHub can roughly
manage users to services.

The following authenticators are included with JupyterHub:

- **PAMAuthenticator** uses the standard Unix/Linux operating system
  functions to check users.  Roughly, if someone already has access to
  the machine (they can log in by ssh or otherwise), they will be able
  to log in to JupyterHub automatically.  Thus, JupyterHub fills the
  role of a ssh server, but providing a web-browser based way to
  access the machine.


But those are fairly limited, and thus there are [plenty of others to
choose
from](https://github.com/jupyterhub/jupyterhub/wiki/Authenticators).
You can connect to almost any other existing service to manage your
users.  You either use all users from this other service (e.g. your
company), or whitelist only the allowed users (e.g. your group's
Github users).  Some other popular authenticators include:

- **OAuthenticator** uses the standard OAuth protocol to verify users.
  For example, you can easily use Github to authenticate your users -
  people have a "click to login with Github" button.  This is often
  done with a whitelist to only allow certain users.

- **NativeAuthenticator** actually stores its own usernames and
  passwords, unlike most other authenticators.  Thus, you can manage
  all your users within JupyterHUb only.  (include one more example
  here)

- There are authenticators for LTI (learning management systems),
  Shibboleth, Kerberos - and so on.

The authenticator is configured with the
`c.JupyterHub.authenticator_class` configuration option in the
`jupyterhub_config.py` file.

The authenticator runs internally to the Hub process but communicates
with outside services.

If you have trouble logging in, this is usually a problem of the
authenticator.  The authenticator debug information goes to the
JupyterHub logs, but there may also be hints in whatever external
services you are using.

### Spawners

The **spawner** is the real core of JupyterHub: when someone wants a
notebook server, it finds resources and starts the server.  It could
run on the current server, on another server, on some cloud service,
or even more.  They can limit resources (CPU, memory) or isolate users
from each other - if the spawner supports it.  They can also do no
limiting and allow any user to access any other user's files if they
are not configured properly.

Some basic spawners included in JupyterHub is:

**LocalProcessSpawner** is build in to JupyterHub and basically starts
tries to switch user to the given username and start Jupyter.  It
requires that the hub be run as root (because only root has permission
to start processes as other user IDs).  LocalProcessSpawner is no
different than a user logging in with something like `ssh` and running
jobs.  PAMAuthenticator and LocalProcessSpawner is the most basic way
of using JupyterHub (and what it does out of the box) and makes the
hub not too dissimilar to an advanced ssh server.

There are many more advanced fancy spawners:

- **SudoSpawner** is like LocalProcessSpawner but lets you run
  JupyterHub without root.  sudo has to be configured to allow the
  hub's user to run processes under other user IDs.

- **SystemdSpawner** uses Systemd to start other processes.  It can
  isolate users from each other and provide some limits.

- **DockerSpawner** runs stuff in Docker, a containerization system.
  This lets you fully isolate users, limit CPU, memory, and provide
  other operating system images to fully customize the environment.

- **KubeSpawner** runs on the Kubernetes, a cloud orchestration
  system.  The spawner can easily limit users and provide cloud
  scaling - but the spawner doesn't actually do that, Kubernetes does.

- **BatchSpawner** runs on computer clusters with batch queuing
  systems.  The user processes are run as batch jobs, having access to
  all the data and software that the users normally will.

In short, spawners are the interface to the rest of the operating
system, and to configure them right you need to know a bit about how
the corresponding operating system service works.

The spawner is responsible for the environment of the single-user
notebook servers (described in the next section).  In the end, it just
makes a choice about how to start these processes: for example, the
Docker spawner starts a normal Docker container and runs the right
command inside of it.  Thus, the spawner is responsible for setting
what kind of software and data is available to the user.

The spawner runs internally to the Hub process but communicates with
outside services.  It is configured by `c.JupyterHub.spawner_class` in
`jupyterhub_config.py`.

If a user tries to launch a notebook server and it doesn't work, the
error is usually with the spawner or the notebook server (as described
in the next section).  Each spawner outputs some logs to the main
JupyterHub logs, but may also have logs in other places depending on
what services it interacts with (for example, the Docker spawner
somehow puts logs in the Docker system services).


### Proxy

Previously, we said that the hub is between the user and the user's
notebook servers.  It actually isn't directly between, because the
JupyterHub **proxy** relays connections between the users and their
single-user notebook servers.  What this basically means is that the
hub itself can shut down, and if the proxy can continue to allow users
to communicate with their notebook servers.  (This just further
emphasizes that the hub is responsible for starting, not running, the
notebooks).  By default, the hub starts the proxy automatically (so
that you don't realize there is a separate proxy) and stops the proxy
when the hub stops (so that connections get interrupted).  But when
you [configure the proxy to run
separately](https://jupyterhub.readthedocs.io/en/stable/reference/separate-proxy.html),
your users connections will stay working even without the hub.

The default proxy is **ConfigurableHttpProxy** which is simple but
effective.  A more advanced option is the **Traefik Proxy**, which
gives you redundancy and high-availability.

When users "connect to JupyterHub", they *always* first connect to the
proxy and the proxy relays the connection to the hub.  Thus, the proxy
is responsible for SSL and accepting connections from the rest of the
internet.

The hub has to connect to the proxy to adjust the routes (The web path
`/user/someone` goes to the server of someone at a certain address).
The proxy has to be able to connect to both the hub and all the
single-user servers.

The proxy always runs as a separate process to JupyterHub (even though
JupyterHub can start it for you).  JupyterHub has one set of
configuration options for the proxy addresses (`bind_url`) and one for
the hub (`bind_url`).  If `bind_url` is given, it is just passed to
the automatic proxy to tell it what to do.

If you have problems after users are redirected to their single-user
notebook servers, or making the first connection to the hub, it is
usually caused by the proxy.  The ConfigurableHttpProxy's logs are
mixed with JupyterHub's logs if it's started through the hub (the
default case), otherwise from whatever system runs the proxy (if you
do it, you'll know).

### Services

JupyterHub has the concept of **services**, which are other web
services started by the hub, but otherwise are not really related to
the hub itself.  They are often used to do things related to Jupyter
(things that user interacts with, usually not the hub), but could
always be run some other way.  Running from the hub provides an easy
way to get Hub API tokens and authenticate users against the hub.

The configuration option `c.JupyterHub.services` (??) is used to start
services from the hub.

Let's use the often-requested question of *sharing files using
hubshare* as an example.  Hubshare would work as an external service
which user notebooks talk to and use Hub authentication, but otherwise
it isn't directly a matter of the hub.  You could equally well share
files by other extensions to the single-user notebook servers or
configuring the spawners to access shared storage spaces.

When a service is started from JupyterHub automatically, its logs are
included in the JupyterHub logs.



## Single-user notebook server

The **single-user notebook server** is the same thing you get by
running `jupyter notebook` or `jupyter lab` from the command line -
the actual Jupyter user interface for a single person.

The role of the spawner is to start this server - basically, running
the command `jupyter notebook`.
Actually it doesn't run that, it runs `jupyterhub-singleuser` which
first communicates with the hub to say "I'm alive" before running a
completely normal Jupyter server.  The single-user server can be
JupyterLab or classic notebooks.  By this point, the hub is almost
completely out of the picture (the web traffic is going through proxy
unchanged).  By this time, the spawner has already decided the
environment which this single-user server will have and the
single-user server has to deal with that.

The spawner starts the server using `jupyterhub-singleuser` with some
environment variables like `JUPYTERHUB_API_TOKEN` and
`JUPYTERHUB_BASE_URL` which tell the single-user server how to connect
back to the hub in order to say that it's ready.

The single-user server options are **JupyterLab** and **classic
Jupyter Notebook**.  Really, there isn't that much difference between
them, they run through the same backend server process and the web
frontend is an option when it is starting.  The spawner can choose the
command line when it starts the single-user server.  Extensions are a
property of the single-user server (in two parts: there can be a part
that runs in server process, and parts that run in javascript in lab
or notebook).

After the single-user notebook server is started, any errors are only
an issue of the single-user notebook server.  Sometimes, it seems like
the spawner is failing, but really the spawner is working but the
single-user notebook server dies right away (in this case, you need to
find the problem with the single-user server and adjust the spawner to
start it correctly).  This can happen, for example, if the spawner
doesn't set an environment variable or doesn't provide storage.

The single-user server's logs are handled by the spawner, so if you
notice problems at this phase you need to check your spawner for
instructions for accessing the single-user logs.  For example, the
LocalProcessSpawner logs are just outputted to the same JupyterHub
output logs (TODO is this correct?), the SystemdSpawner logs are
written to the Systemd journal, Docker and Kubernetes logs are written
to Docker and Kubernetes respectively, and batchspawner output goes to
the normal output places of batch jobs and is an explicit
configuration option of the spawner.


### Notebook

**(Jupyter) Notebook** is the classic interface, where each notebook
opens in a separate tab.

Does anything need to be said here?

### Lab

**JupyterLab** is the new interface, where multiple notebooks are
openable in the same tab in an IDE-like environment.  JupyterLab is
run thorugh the same server file, but at a path `/lab` instead of
`/tree`.

Both Notebook and Lab use the same `.ipynb` file format.

Does anything need to be said here?
- how extensions work in lab compared to notebook



## Kernel

Normally, our tour of the Jupyter ecosystem would stop here.  But,
since if you've read this far you probably need to know every last
bit, let's go further and talk about the kernels.  The commands you
run in the notebook session are not executed in the same process as
the notebook itself, but in a separate **kernel**.  There are [many
kernels
available](https://github.com/jupyter/jupyter/wiki/Jupyter-kernels).

As a basic approximation, a **Jupyter kernel** is a process which
accepts commands (cells that are run) and returns the output to
Jupyter to display.  One example is the **IPython Jupyter kernel**,
which runs Python and adds the IPython magic functions (`%`, `%%`,
`!`, etc. commands).  There is nothing special about it, it can be
considered a *normal Python process*.  Like we said above, the kernel
process can be approximated as a process that takes commands on stdin
and returns stuff on stdout.  Actually, a kernel is more fancy,
because it can communicate over the network and add in magic commands.

Kernel communication is via the the ZeroMQ protocol on the local
computer.  Kernels are separate processes from the main single-user
notebook server (and thus obviously, different from the JupyterHub
process and everything else).  By default (and unless you do something
special), kernels share the same environment as the notebook server
(data, resource limits, permissions, user id, etc.).  But there are
things like the Jupyter Kernel Gateway / Enterprise Gateway, which
allow you to run the kernels on a different machine and possibly with
a different environment.

What does this mean?  There is yet *another* layer of configurability.
Each kernel can run a different programming language, with different
software, and so on.  By default, they would run in the same
environment as the single-user notebook server, and the most common
other way they are configured is by
running in different Python virtual environments or conda
environments.  They can be started and killed independently (there is
normally one per notebook you have open).  The kernels is what uses
most of your memory and CPU if you have large amounts of data open or
are using a lot of compute power.

You can list your installed kernels with `jupyter kernelspec list`.
If you look at one of `kernel.json` files in those directories, you
will see exactly what command is run.  These are normally
automatically made by the kernels, but can be edited as needed.  [The
spec](https://jupyter-client.readthedocs.io/en/stable/kernels.html)
tells you even more.

The kernel has to be reachable by the single-user notebook server.

If you get problems with "Kernel died" or some other error in a single
notebook but the single-user notebook server stays working, it is
usually a problem with the kernel.  It could be that you are trying to
use more resources than you are allowed and the symptom is the kernel
getting killed.  It could be that it crashes for some other reason.
The debug logs for the kernel are normally mixed in with the
single-user notebook server logs.



### JupyterHub distributions

There are several "distributions" which automatically install all of
the things above and configure them for a certain purpose.  They are
good ways to get started, but if you are doing very custom things
eventually it may become hard to adapt them to your needs.

* **Zero to JupyterHub with Kubernetes** installs an entire scaleable
  system using Kubernetes.  Uses KubeSpawner, ....Authenticator, ....

* **The Littlest JupyterHub** installs JupyterHub on a single system
  using SystemdSpawner and NativeAuthenticator (which manages users
  itself).

* **JupyterHub the hard way** takes you through everything yourself.
  It is a natural companion to this guide, since you get to experience
  every little bit.



## I want to...

**Share files between users**.  Spawner to share data, or
JupyterNotebook/Lab user interface + some service for distributing
files.


## What's next?

Now you know everything.  Well, you know how everything relates, but
there are still plenty of details, implementations, and exceptions.
When setting up JupyterHub, the first step is to consider the above
layers and see what options are suitable for you.  Then, put
everything together.
