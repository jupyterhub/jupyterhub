# Bootstrapping your users

Before spawning a notebook to the user, it could be useful to 
do some preparation work in a bootstrapping process.

Common use cases are:

*Providing writeable storage for LDAP users*

Your Jupyterhub is configured to use the LDAPAuthenticator and DockerSpawer.

* The user has no file directory on the host since your are using LDAP.
* When a user has no directory and DockerSpawner wants to mount a volume,
the spawner will use docker to create a directory.
Since the docker daemon is running as root, the generated directory for the volume 
mount will not be writeable by the `jovyan` user inside of the container. 
For the directory to be useful to the user, the permissions on the directory 
need to be modified for the user to have write access.

*Prepopulating Content*

Another use would be to copy initial content, such as tutorial files or reference
 material, into the user's space when a notebook server is newly spawned.

You can define your own bootstrap process by implementing a `pre_spawn_hook` on any spawner.
The Spawner itself is passed as parameter to your hook and you can easily get the contextual information out of the spawning process. 

Similarly, there may be cases where you would like to clean up after a spawner stops.
You may implement a `post_stop_hook` that is always executed after the spawner stops.

If you implement a hook, make sure that it is *idempotent*. It will be executed every time
a notebook server is spawned to the user. That means you should somehow
ensure that things which should run only once are not running again and again.
For example, before you create a directory, check if it exists.

Bootstrapping examples:

### Example #1 - Create a user directory

Create a directory for the user, if none exists

```python

# in jupyterhub_config.py  
import os
def create_dir_hook(spawner):
    username = spawner.user.name # get the username
    volume_path = os.path.join('/volumes/jupyterhub', username)
    if not os.path.exists(volume_path):
        # create a directory with umask 0755 
        # hub and container user must have the same UID to be writeable
        # still readable by other users on the system
        os.mkdir(volume_path, 0o755)
        # now do whatever you think your user needs
        # ...
        pass

# attach the hook function to the spawner
c.Spawner.pre_spawn_hook = create_dir_hook
```

### Example #2 - Run `mkhomedir_helper`

Many Linux distributions provide a script that is responsible for user homedir bootstrapping: `/sbin/mkhomedir_helper`. To make use of it, you can use

```python
def create_dir_hook(spawner):
    username = spawner.user.name
    if not os.path.exists(os.path.join('/volumes/jupyterhub', username)):
        subprocess.call(["sudo", "/sbin/mkhomedir_helper", spawner.user.name])

# attach the hook function to the spawner
c.Spawner.pre_spawn_hook = create_dir_hook
```

and make sure to add

```
jupyterhub ALL = (root) NOPASSWD: /sbin/mkhomedir_helper
```

in a new file in `/etc/sudoers.d`, or simply in `/etc/sudoers`.

All new home directories will be created from `/etc/skel`, so make sure to place any custom homedir-contents in there.

### Example #3 - Run a shell script 

You can specify a plain ole' shell script (or any other executable) to be run 
by the bootstrap process.

For example, you can execute a shell script and as first parameter pass the name 
of the user:

```python

# in jupyterhub_config.py    
from subprocess import check_call
import os
def my_script_hook(spawner):
    username = spawner.user.name # get the username
    script = os.path.join(os.path.dirname(__file__), 'bootstrap.sh')
    check_call([script, username])

# attach the hook function to the spawner
c.Spawner.pre_spawn_hook = my_script_hook

```

Here's an example on what you could do in your shell script. See also 
`/examples/bootstrap-script/`

```bash
#!/bin/bash

# Bootstrap example script
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

# - The first parameter for the Bootstrap Script is the USER.
USER=$1
if [ "$USER" == "" ]; then
    exit 1
fi
# ----------------------------------------------------------------------------


# This example script will do the following:
# - create one directory for the user $USER in a BASE_DIRECTORY (see below)
# - create a "tutorials" directory within and download and unzip 
#   the PythonDataScienceHandbook from GitHub

# Start the Bootstrap Process
echo "bootstrap process running for user $USER ..."

# Base Directory: All Directories for the user will be below this point
BASE_DIRECTORY=/volumes/jupyterhub/

# User Directory: That's the private directory for the user to be created, if none exists
USER_DIRECTORY=$BASE_DIRECTORY/$USER

if [ -d "$USER_DIRECTORY" ]; then
    echo "...directory for user already exists. skipped"
    exit 0 # all good. nothing to do.
else
    echo "...creating a directory for the user: $USER_DIRECTORY"
    mkdir $USER_DIRECTORY

    echo "...initial content loading for user ..."
    mkdir $USER_DIRECTORY/tutorials
    cd $USER_DIRECTORY/tutorials
    wget https://github.com/jakevdp/PythonDataScienceHandbook/archive/master.zip
    unzip -o master.zip
    rm master.zip
fi

exit 0
```
