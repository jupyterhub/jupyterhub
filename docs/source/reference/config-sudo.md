# Run JupyterHub without root privileges using `sudo`

**Note:** Setting up `sudo` permissions involves many pieces of system
configuration. It is quite easy to get wrong and very difficult to debug.
Only do this if you are very sure you must.

## Overview

There are many Authenticators and Spawners available for JupyterHub. Some, such
as DockerSpawner or OAuthenticator, do not need any elevated permissions. This
document describes how to get the full default behavior of JupyterHub while
running notebook servers as real system users on a shared system without 
running the Hub itself as root.

Since JupyterHub needs to spawn processes as other users, the simplest way
is to run it as root, spawning user servers with [setuid](http://linux.die.net/man/2/setuid).
But this isn't especially safe, because you have a process running on the
public web as root.

A **more prudent way** to run the server while preserving functionality is to
create a dedicated user with `sudo` access restricted to launching and
monitoring single-user servers.

## Create a user

To do this, first create a user that will run the Hub:

```bash
sudo useradd rhea
```

This user shouldn't have a login shell or password (possible with -r).

## Set up sudospawner

Next, you will need [sudospawner](https://github.com/jupyter/sudospawner)
to enable monitoring the single-user servers with sudo:

```bash
sudo python3 -m pip install sudospawner
```

Now we have to configure sudo to allow the Hub user (`rhea`) to launch
the sudospawner script on behalf of our hub users (here `zoe` and `wash`).
We want to confine these permissions to only what we really need.

## Edit `/etc/sudoers`

To do this we add to `/etc/sudoers` (use `visudo` for safe editing of sudoers):

- specify the list of users `JUPYTER_USERS` for whom `rhea` can spawn servers
- set the command `JUPYTER_CMD` that `rhea` can execute on behalf of users
- give `rhea` permission to run `JUPYTER_CMD` on behalf of `JUPYTER_USERS` 
  without entering a password


For example:

```bash
# comma-separated list of users that can spawn single-user servers
# this should include all of your Hub users
Runas_Alias JUPYTER_USERS = rhea, zoe, wash

# the command(s) the Hub can run on behalf of the above users without needing a password
# the exact path may differ, depending on how sudospawner was installed
Cmnd_Alias JUPYTER_CMD = /usr/local/bin/sudospawner

# actually give the Hub user permission to run the above command on behalf
# of the above users without prompting for a password
rhea ALL=(JUPYTER_USERS) NOPASSWD:JUPYTER_CMD
```

It might be useful to modify `secure_path` to add commands in path.

As an alternative to adding every user to the `/etc/sudoers` file, you can
use a group in the last line above, instead of `JUPYTER_USERS`:

```bash
rhea ALL=(%jupyterhub) NOPASSWD:JUPYTER_CMD
```

If the `jupyterhub` group exists, there will be no need to edit `/etc/sudoers`
again. A new user will gain access to the application when added to the group:

```bash
$ adduser -G jupyterhub newuser
```

## Test `sudo` setup

Test that the new user doesn't need to enter a password to run the sudospawner
command.

This should prompt for your password to switch to rhea, but *not* prompt for
any password for the second switch. It should show some help output about
logging options:

```bash
$ sudo -u rhea sudo -n -u $USER /usr/local/bin/sudospawner --help
Usage: /usr/local/bin/sudospawner [OPTIONS]
    
Options:
    
--help          show this help information
...
```

And this should fail:

```bash
$ sudo -u rhea sudo -n -u $USER echo 'fail'
sudo: a password is required
```

## Enable PAM for non-root

By default, [PAM authentication](http://en.wikipedia.org/wiki/Pluggable_authentication_module)
is used by JupyterHub. To use PAM, the process may need to be able to read
the shadow password database.

### Shadow group (Linux)

**Note:** On Fedora based distributions there is no clear way to configure
the PAM database to allow sufficient access for authenticating with the target user's password
from JupyterHub. As a workaround we recommend use an
[alternative authentication method](https://github.com/jupyterhub/jupyterhub/wiki/Authenticators).

```bash
$ ls -l /etc/shadow
-rw-r-----  1 root shadow   2197 Jul 21 13:41 shadow
```

If there's already a shadow group, you are set. If its permissions are more like:

```bash
    $ ls -l /etc/shadow
    -rw-------  1 root wheel   2197 Jul 21 13:41 shadow
```

Then you may want to add a shadow group, and make the shadow file group-readable:

```bash
$ sudo groupadd shadow
$ sudo chgrp shadow /etc/shadow
$ sudo chmod g+r /etc/shadow
```

We want our new user to be able to read the shadow passwords, so add it to the shadow group:

```bash
    $ sudo usermod -a -G shadow rhea
```

If you want jupyterhub to serve pages on a restricted port (such as port 80 for http), 
then you will need to give `node` permission to do so:

```bash
sudo setcap 'cap_net_bind_service=+ep' /usr/bin/node
```
However, you may want to further understand the consequences of this.

You may also be interested in limiting the amount of CPU any process can use
on your server. `cpulimit` is a useful tool that is available for many Linux
distributions' packaging system. This can be used to keep any user's process
from using too much CPU cycles. You can configure it accoring to [these
instructions](http://ubuntuforums.org/showthread.php?t=992706).


### Shadow group (FreeBSD)

**NOTE:** This has not been tested and may not work as expected.

```bash
$ ls -l /etc/spwd.db /etc/master.passwd
-rw-------  1 root  wheel   2516 Aug 22 13:35 /etc/master.passwd
-rw-------  1 root  wheel  40960 Aug 22 13:35 /etc/spwd.db
```

Add a shadow group if there isn't one, and make the shadow file group-readable:

```bash
$ sudo pw group add shadow
$ sudo chgrp shadow /etc/spwd.db
$ sudo chmod g+r /etc/spwd.db
$ sudo chgrp shadow /etc/master.passwd
$ sudo chmod g+r /etc/master.passwd
```

We want our new user to be able to read the shadow passwords, so add it to the 
shadow group:

```bash
$ sudo pw user mod rhea -G shadow
```

## Test that PAM works

We can verify that PAM is working, with:

```bash
$ sudo -u rhea python3 -c "import pamela, getpass; print(pamela.authenticate('$USER', getpass.getpass()))"
Password: [enter your unix password]
```

## Make a directory for JupyterHub

JupyterHub stores its state in a database, so it needs write access to a directory.
The simplest way to deal with this is to make a directory owned by your Hub user,
and use that as the CWD when launching the server.

```bash
$ sudo mkdir /etc/jupyterhub
$ sudo chown rhea /etc/jupyterhub
```

## Start jupyterhub

Finally, start the server as our newly configured user, `rhea`:

```bash
$ cd /etc/jupyterhub
$ sudo -u rhea jupyterhub --JupyterHub.spawner_class=sudospawner.SudoSpawner
```                                                                             

And try logging in.

## Troubleshooting: SELinux

If you still get a generic `Permission denied` `PermissionError`, it's possible SELinux is blocking you.  
Here's how you can make a module to allow this.
First, put this in a file  named `sudo_exec_selinux.te`:

```bash
module sudo_exec_selinux 1.1;

require {
        type unconfined_t;
        type sudo_exec_t;
        class file { read entrypoint };
}

#============= unconfined_t ==============
allow unconfined_t sudo_exec_t:file entrypoint;
```

Then run all of these commands as root:

```bash
$ checkmodule -M -m -o sudo_exec_selinux.mod sudo_exec_selinux.te
$ semodule_package -o sudo_exec_selinux.pp -m sudo_exec_selinux.mod
$ semodule -i sudo_exec_selinux.pp
```

## Troubleshooting: PAM session errors

If the PAM authentication doesn't work and you see errors for
`login:session-auth`, or similar, considering updating to a more recent version
of jupyterhub and disabling the opening of PAM sessions with
`c.PAMAuthenticator.open_sessions=False`.
