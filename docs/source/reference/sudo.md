# Using sudo to run JupyterHub without root privileges

**Note:** setting up sudo permissions involves many pieces of system configuration and is quite easy to get wrong and very difficult to debug. Only do this if you are very sure you have to.

There are many Authenticators and Spawners for JupyterHub. Some (e.g. Docker + GitHub OAuth) do not need any elevated permissions. This document describes how to get the full default behavior of JupyterHub: running notebook servers as real system users on a shared system without running the Hub itself as root.

Since JupyterHub needs to spawn processes as other users (that's kinda the point of it),
the simplest way is to run it as root, spawning user servers with [setuid](http://linux.die.net/man/2/setuid).
But this isn't especially safe, because you have a process running on the public web as root.
Any vulnerability in the JupyterHub process could be pretty catastrophic.

A **more prudent way** to run the server while preserving functionality
is to create a dedicated user with **sudo access restricted to launching and monitoring single-user servers**.

To do this, first create a user that will run the Hub:

    sudo useradd rhea

This user shouldn't have a login shell or password (possible with -r).

Next, you will need the [sudospawner](https://github.com/jupyter/sudospawner) custom Spawner to enable monitoring the single-user servers with sudo:

```bash
sudo pip install sudospawner
```

Now we have to configure sudo to allow the Hub user (`rhea`) to launch the sudospawner script
on behalf of our hub users (here zoe and wash).
We want to confine these permissions to only what we really need.
To do this we add to /etc/sudoers (use `visudo` for safe editing of sudoers): 

1. specify the list of users for whom rhea can spawn servers (JUPYTER_USERS)
2. specify the command that rhea can execute on behalf of users (JUPYTER_CMD)
3. give rhea permission to run JUPYTER_CMD on behalf of JUPYTER_USERS without entering a password

For example:

```bash
# comma-separated whitelist of users that can spawn single-user servers
# this should include all of your Hub users
Runas_Alias JUPYTER_USERS = rhea, zoe, wash

# the command(s) the Hub can run on behalf of the above users without needing a password
# the exact path may differ, depending on how sudospawner was installed
Cmnd_Alias JUPYTER_CMD = /usr/local/bin/sudospawner

# actually give the Hub user permission to run the above command on behalf
# of the above users without prompting for a password
rhea ALL=(JUPYTER_USERS) NOPASSWD:JUPYTER_CMD
```
It might be usefull to modifiy ```secure_path``` to add commands in path.

As an alternative to add every user to the ```/etc/sudoers``` file, you can use a group in the last line, instead of JUPYTER_USERS:
```bash
rhea ALL=(%jupyterhub) NOPASSWD:JUPYTER_CMD
```

Provided that the ```jupyterhub``` group exists, there will be no need to edit ```/etc/sudoers``` again. A new user will gain access to the application easily just getting added to the group:

```bash
$ adduser -G jupyterhub newuser
```

## Test sudo setup:

Test that the new user doesn't need to enter a password to run the sudospawner command:

This should prompt for your password to switch to rhea, but *not* prompt for any password for the second switch. It should show some help output about logging options:

    $ sudo -u rhea sudo -n -u $USER /usr/local/bin/sudospawner --help
    Usage: /usr/local/bin/sudospawner [OPTIONS]
    
    Options:
    
      --help                           show this help information
    ...


And this should fail:

    $ sudo -u rhea sudo -n -u $USER echo 'fail'
    sudo: a password is required

## enabling PAM for non-root

[PAM authentication](http://en.wikipedia.org/wiki/Pluggable_authentication_module) is used by JupyterHub. To use PAM, the process may need to be able to read the shadow password database.

### Linux

    $ ls -l /etc/shadow
    -rw-r-----  1 root shadow   2197 Jul 21 13:41 shadow

If there's already a shadow group, you are set. If its permissions are more like:

    $ ls -l /etc/shadow
    -rw-------  1 root wheel   2197 Jul 21 13:41 shadow

Then you may want to add a shadow group, and make the shadow file group-readable:

    $ sudo groupadd shadow
    $ sudo chgrp shadow /etc/shadow
    $ sudo chmod g+r /etc/shadow

We want our new user to be able to read the shadow passwords, so add it to the shadow group:

    $ sudo usermod -a -G shadow rhea

If you want jupyterhub to serve pages on a restrict port (such as port 80 for http), then you will need to give node permission:

    sudo setcap 'cap_net_bind_service=+ep' /usr/bin/node

However, you may want to further understand the consequences of this.

You may also be interested in limiting the amount of CPU any process can use on your server. `cpulimit` is a useful tool that is available for many Linux distributions' packaging system. This can be used to keep any user's process from using too much CPU cycles. You can configure it accoring to [these instructions](http://ubuntuforums.org/showthread.php?t=992706).


### FreeBSD

**NOTE: This doesn't work yet**

    $ ls -l /etc/spwd.db /etc/master.passwd
    -rw-------  1 root  wheel   2516 Aug 22 13:35 /etc/master.passwd
    -rw-------  1 root  wheel  40960 Aug 22 13:35 /etc/spwd.db

Add a shadow group if there isn't one, and make the shadow file group-readable:

    $ sudo pw group add shadow
    $ sudo chgrp shadow /etc/spwd.db
    $ sudo chmod g+r /etc/spwd.db
    $ sudo chgrp shadow /etc/master.passwd
    $ sudo chmod g+r /etc/master.passwd

We want our new user to be able to read the shadow passwords, so add it to the shadow group:

    $ sudo pw user mod rhea -G shadow

### Test that PAM works

We can verify that PAM is working, with:

    $ sudo -u rhea python3 -c "import pamela, getpass; print(pamela.authenticate('$USER', getpass.getpass()))"
    Password: [enter your unix password]

## Make a Directory for JupyterHub

JupyterHub stores its state in a database, so it needs write access to a directory.
The simplest way to deal with this is to make a directory owned by your Hub user,
and use that as the CWD when launching the server.

    $ sudo mkdir /etc/jupyterhub
    $ sudo chown rhea /etc/jupyterhub

## Finally, start the server as our newly configured user

    $ cd /etc/jupyterhub
    $ sudo -u rhea jupyterhub --JupyterHub.spawner_class=sudospawner.SudoSpawner

And try logging in.

### SELinux

If you still get a generic `Permission denied` `PermissionError`, it's possible SELinux is blocking you.  
Here's how you can make a module to allow this.
First, put this in a file sudo_exec_selinux.te:
```
module sudo_exec 1.1;

require {
        type unconfined_t;
        type sudo_exec_t;
        class file { read entrypoint };
}

#============= unconfined_t ==============
allow unconfined_t sudo_exec_t:file entrypoint;
```
Then run all of these commands as root:

    $ checkmodule -M -m -o sudo_exec_selinux.mod sudo_exec_selinux.te
    $ semodule_package -o sudo_exec_selinux.pp -m sudo_exec_selinux.mod
    $ semodule -i sudo_exec_selinux.pp


### PAM session errors

If the PAM authentication doesn't work and you see errors for `login:session-auth`, or similar, considering updating to `master` and/or incorporating this commit https://github.com/jupyter/jupyterhub/commit/40368b8f555f04ffdd662ffe99d32392a088b1d2 and configuration option, `c.PAMAuthenticator.open_sessions = False`.
