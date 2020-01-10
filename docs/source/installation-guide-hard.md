# Install Jupyterhub and Jupyterlab from the ground up

The combination of [Jupyterhub](https://jupyterhub.readthedocs.io) and [Jupyterlab](https://jupyterlab.readthedocs.io)
is a great way to make shared computing resources available to a group.

These instructions are a guide for a manual, 'bare metal' install of [Jupyterhub](https://jupyterhub.readthedocs.io) 
and [Jupyterlab](https://jupyterlab.readthedocs.io). This is ideal for running on a single server: build a beast
of a machine and share it within your lab, or use a virtual machine from any VPS or cloud provider.

This guide has similar goals to [The Littlest Jupyerhub](https://the-littlest-jupyterhub.readthedocs.io) setup
script. However, instead of bundling all these step for you into one installer, we will perform every step manually.
This makes it easy to customize any part (e.g. if you want to run other services on the same system and need to make them
work together), as well as giving you full control and understanding of your setup.


## Prerequisites

Your own server with administrator (root) access. Each user who will access JupyterHub should have a
standard user account on the machine. The install will be done through the command line - useful if you log into your 
machine remotely using SSH.

This tutorial was tested on **Ubuntu 18.04**. No other Linux distributions have been tested, but the instructions 
should be reasonably straightforward to adapt.


## Goals

Jupyterlab enables access to a multiple 'kernels', each one being a given environment for a given language. The most
common is a Python environment, for scientific computing usually one managed by the `conda` package manager.

This guide will set up Jupyterhub and Jupyterlab seperately from the Python environment. In other words, we treat
Jupyterhub+Jupyterlab as a 'app' or webservice, which will connect to the kernels available on the system. Specifically:

- We will create an installation of Jupyterhub and Jupyterlab using a virtualenv under `/opt` using the system Python.

- We will install conda globally.

- We will create a shared conda environment which can be used (but not modified) by all users.

- We will show how users can create their own private conda environments, where they can install whatever they like.


The default JupyterHub Authenticator uses PAM to authenticate system users with their username and password. One can [choose the authenticator](https://jupyterhub.readthedocs.io/en/stable/reference/authenticators.html#authenticators) that best suits their needs. In this guide we will use the default Authenticator because it makes it easy for everyone to manage data 
in their home folder and to mix and match different services and access methods (e.g. SSH) which all work using the 
Linux system user accounts.

Another goal of this guide is to use system provided packages wherever possible. This has the advantage that these packages
get automatic patches and security updates (be sure to turn on automatic updates in Ubuntu). This means less maintenance
work and a more reliable system.

## Part 1: Jupyterhub and Jupyterlab

### Setup the Jupyterhub and Jupyterlab in a virtual environment

First we create a virtual environment under '/opt/jupyterhub'. The '/opt' folder is where apps not belonging to the operating
system are [commonly installed](https://unix.stackexchange.com/questions/11544/what-is-the-difference-between-opt-and-usr-local).
Both jupyterlab and jupyterhub will be installed into this virtualenv. Create it with the command:

```sh
sudo python3 -m venv /opt/jupyterhub/
```

Now we use pip to install the required Python packages into the new virtual environment. Be sure to install 
`wheel` first. Since we are separating the user interface from the computing kernels, we don't install 
any Python scientific packages here. The only exception is `ipywidgets` because this is needed to allow connection 
between interactive tools running in the kernel and the user interface. 

Note that we use 
`/opt/jupyterhub/bin/python3 -m pip install` each time - this [makes sure](https://snarky.ca/why-you-should-use-python-m-pip/)
that the packages are installed to the correct virtual environment.

Perform the install using the following commands:

```sh
sudo /opt/jupyterhub/bin/python3 -m pip install wheel
sudo /opt/jupyterhub/bin/python3 -m pip install jupyterhub jupyterlab
sudo /opt/jupyterhub/bin/python3 -m pip install ipywidgets
```

Jupyterhub also currently defaults to requiring `configurable-http-proxy`, which needs `nodejs` and `npm`. The versions
of these available in Ubuntu therefore need to be installed first (they are a bit old but this is ok here):

```sh
sudo apt install nodejs npm
```

Then install `configurable-http-proxy`:

```sh
npm install -g configurable-http-proxy
```

### Create the configuration for Jupyterhub

Now we start creating configuration files. To keep everything together, we put all the configuration into the folder
created for the virtualenv, under `/opt/jupyterhub/etc/`. For each thing needing configuration, we will create a further
subfolder and necessary files. 

First create the folder for Jpyterhub configuration and navigate to it:

```sh
sudo mkdir -p /opt/jupyterhub/etc/jupyterhub/
cd /opt/jupyterhub/etc/jupyterhub/
```
Then generate the default configuration file

```sh
sudo /opt/jupyterhub/bin/jupyterhub --generate-config
```
This will produce the default configuration file `/opt/jupyterhub/etc/jupyterhub/jupyterhub_config.py`

### Setup Systemd service

We will setup Jupyterhub to run as a system service using Systemd (which is responsible for managing all services and 
servers that run on startup in Ubuntu). We will create a service file in a suitable location in the virtualenv folder 
and then link it to the system services. First create the folder for the service file:

```sh
mkdir -p /opt/jupyterhub/etc/systemd
```

Then create a text file using your [favourite editor](https://micro-editor.github.io/) at
```sh
/opt/jupyterhub/etc/systemd/jupyterhub.service
```

Paste the following into the file:

```
[Unit]
Description=Jupyterhub
After=syslog.target network.target

[Service]
User=root
Environment="PATH=/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/opt/jupyterhub/venv/bin"
ExecStart=/opt/jupyterhub/bin/jupyterhub -f /opt/jupyterhub/etc/jupyterhub/jupyterhub_config.py

[Install]
WantedBy=multi-user.target
```

This sets up the environment to use the virtual environment we created, tells Systemd how to start jupyterhub using
the configuration file we created, specifies that jupyterhub will be started as the `root` user (needed so that it can
start jupyter on behalf of other logged in users), and specifies that jupyterhub should start on boot after the network
is enabled.

Finally, we need to make systemd aware of our service file. First we symlink our file into systemd's directory:

```sh
sudo ln -s /opt/jupyterhub/etc/systemd/jupyterhub.service /etc/systemd/system/jupyterhub.service
```

Then tell systemd to reload its configuration files

```sh
sudo systemctl daemon-reload
```

And finally enable the service 

```sh
sudo systemctl enable jupyterhub.service
```

The service will start on reboot, but we can start it straight away using:

```sh
sudo systemctl start jupyterhub.service
```

...and check that it's running using:

```sh
sudo systemctl status jupyterhub.service
```

You should now be already be able to access jupyterhub using `<your servers ip>:8000` (assuming you haven't already set
up a firewall or something). However, when you log in the jupyter notebooks will be trying to use the Python virtualenv
that was created to install Jupyterhub, this is not what we want. So on to part 2   

## Part 2: Conda environments

### Install conda for the whole system

We will use `conda` to manage Python environments. We will install the officially maintained `conda` packages for Ubuntu,
this means they will get automatic updates with the rest of the system. Setup repo for the official Conda debian packages,
instructions are copied from [here](https://docs.conda.io/projects/conda/en/latest/user-guide/install/rpm-debian.html):

Install Anacononda public gpg key to trusted store
```sh
curl https://repo.anaconda.com/pkgs/misc/gpgkeys/anaconda.asc | gpg --dearmor > conda.gpg 
sudo install -o root -g root -m 644 conda.gpg /etc/apt/trusted.gpg.d/
```

Add Debian repo

```sh
sudo echo "deb [arch=amd64] https://repo.anaconda.com/pkgs/misc/debrepo/conda stable main" > /etc/apt/sources.list.d/conda.list
```

Install conda

```sh
sudo apt update
sudo apt install conda
```

This will install conda into the folder `/opt/conda/`, with the conda command available at `/opt/conda/bin/conda`.

Finally, we can make conda more easily available to users by symlinking the conda shell setup script to the profile
'drop in' folder so that it gets run on login

```sh
sudo ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh
```

### Install a default conda environment for all users

First create a folder for conda envs (might exist already):
```sh
sudo mkdir /opt/conda/envs/
```

Then create a conda environment to your liking within that folder. Here we have called it 'python' because it will
be the obvious default - call it whatever you like. You can install whatever you like into this environment, but you MUST at least install `ipykernel`.

```sh
sudo /opt/conda/bin/conda create --prefix /opt/conda/envs/python python=3.7 ipykernel
```

Once your env is set up as desired, make it visible to Jupyter by installing the kernel spec. There are two options here: 

1 ) Install into the jupyterhub virtualenv - this ensures it overrides the default python version.

```sh
sudo /opt/conda/envs/python/bin/python -m ipykernel install --prefix=/opt/jupyterhub/ --name 'python' --display-name "Python (default)"
```

2 ) Install it system-wide by putting it into `/usr/local`, where any Jupyter install will look for kernels
```sh
sudo /opt/conda/envs/python/bin/python -m ipykernel install --prefix /usr/local/ --name 'python' --display-name "Python (default)"
````

### Setting up users' own conda environments

There is relatively little to do here, users will have to set up their own environments using the shell. On login they
should run `conda init` or  `/opt/conda/bin/conda`. The can then use conda however they like to set up their environment,
although they must also install `ipykernel`. Once done, they can enable their kernel using:

```sh
/path/to/kernel/env/bin/python -m ipykernel install --name 'python-my-env' --display-name "Python My Env"
```

This will place the kernel spec into their home folder, where Jupyter will look for it on startup.


## Setting up a reverse proxy 

The guide so far results in jupyterhub running on port 8000. It is not generally advisable to run open web services in 
this way - instead, use a reverse proxy running on standard HTTP/HTTPS ports.


### Using Nginx
Nginx is a mature and established web server and reverse proxy and is easy to install using `sudo apt install nginx`.
Details on using Nginx as a reverse proxy can be found elsewhere.

Often a useful thing to do is to setup jupyterhub to work at a given url path e.g. `<your-server-address>/jupyter`. 
This could be useful for example if you are running several services on the server (e.g. you might have RStudio server 
running also). 

To achieve this needs a few tweaks to both the Jupyterhub configuration and the Nginx config. First, edit the
configuration file `/opt/jupyterhub/etc/jupyterhub/jupyterhub_config.py` and add the line:

```python
c.JupyterHub.bind_url = 'http://:8000/jupyter'
```

where `/jupyter` will be the relative URL of the server.

Now Nginx must be configured with a to pass all traffic from `/jupyter` to the the local address `127.0.0.1:8000`.
Add the following snippet to your nginx configuration file (e.g. `/etc/nginx/sites-available/default`).
You will need to restart nginx for the new configuration to take effect.

```
  location /jupyter/ {    
    # NOTE important to also set base url of jupyterhub to /jupyter in its config
    proxy_pass http://127.0.0.1:8000;

    proxy_redirect   off;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # websocket headers
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;

  }
```

