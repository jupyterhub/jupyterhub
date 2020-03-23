# Install JupyterHub and JupyterLab from the ground up

The combination of [JupyterHub](https://jupyterhub.readthedocs.io) and [JupyterLab](https://jupyterlab.readthedocs.io)
is a great way to make shared computing resources available to a group.

These instructions are a guide for a manual, 'bare metal' install of [JupyterHub](https://jupyterhub.readthedocs.io)
and [JupyterLab](https://jupyterlab.readthedocs.io). This is ideal for running on a single server: build a beast
of a machine and share it within your lab, or use a virtual machine from any VPS or cloud provider.

This guide has similar goals to [The Littlest JupyterHub](https://the-littlest-jupyterhub.readthedocs.io) setup
script. However, instead of bundling all these step for you into one installer, we will perform every step manually.
This makes it easy to customize any part (e.g. if you want to run other services on the same system and need to make them
work together), as well as giving you full control and understanding of your setup.


## Prerequisites

Your own server with administrator (root) access. This could be a local machine, a remotely hosted one, or a cloud instance
or VPS. Each user who will access JupyterHub should have a standard user account on the machine. The install will be done
through the command line - useful if you log into your machine remotely using SSH.

This tutorial was tested on **Ubuntu 18.04**. No other Linux distributions have been tested, but the instructions
should be reasonably straightforward to adapt.


## Goals

JupyterLab enables access to a multiple 'kernels', each one being a given environment for a given language. The most
common is a Python environment, for scientific computing usually one managed by the `conda` package manager.

This guide will set up JupyterHub and JupyterLab seperately from the Python environment. In other words, we treat
JupyterHub+JupyterLab as a 'app' or webservice, which will connect to the kernels available on the system. Specifically:

- We will create an installation of JupyterHub and JupyterLab using a virtualenv under `/opt` using the system Python.

- We will install conda globally.

- We will create a shared conda environment which can be used (but not modified) by all users.

- We will show how users can create their own private conda environments, where they can install whatever they like.


The default JupyterHub Authenticator uses PAM to authenticate system users with their username and password. One can
[choose the authenticator](https://jupyterhub.readthedocs.io/en/stable/reference/authenticators.html#authenticators)
that best suits their needs. In this guide we will use the default Authenticator because it makes it easy for everyone to manage data
in their home folder and to mix and match different services and access methods (e.g. SSH) which all work using the
Linux system user accounts. Therefore, each user of JupyterHub will need a standard system user account.

Another goal of this guide is to use system provided packages wherever possible. This has the advantage that these packages
get automatic patches and security updates (be sure to turn on automatic updates in Ubuntu). This means less maintenance
work and a more reliable system.

## Part 1: JupyterHub and JupyterLab

### Setup the JupyterHub and JupyterLab in a virtual environment

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

Note that we use `/opt/jupyterhub/bin/python3 -m pip install` each time - this [makes sure](https://snarky.ca/why-you-should-use-python-m-pip/)
that the packages are installed to the correct virtual environment.

Perform the install using the following commands:

```sh
sudo /opt/jupyterhub/bin/python3 -m pip install wheel
sudo /opt/jupyterhub/bin/python3 -m pip install jupyterhub jupyterlab
sudo /opt/jupyterhub/bin/python3 -m pip install ipywidgets
```

JupyterHub also currently defaults to requiring `configurable-http-proxy`, which needs `nodejs` and `npm`. The versions
of these available in Ubuntu therefore need to be installed first (they are a bit old but this is ok for our needs):

```sh
sudo apt install nodejs npm
```

Then install `configurable-http-proxy`:

```sh
sudo npm install -g configurable-http-proxy
```

### Create the configuration for JupyterHub

Now we start creating configuration files. To keep everything together, we put all the configuration into the folder
created for the virtualenv, under `/opt/jupyterhub/etc/`. For each thing needing configuration, we will create a further
subfolder and necessary files.

First create the folder for the JupyterHub configuration and navigate to it:

```sh
sudo mkdir -p /opt/jupyterhub/etc/jupyterhub/
cd /opt/jupyterhub/etc/jupyterhub/
```
Then generate the default configuration file

```sh
sudo /opt/jupyterhub/bin/jupyterhub --generate-config
```
This will produce the default configuration file `/opt/jupyterhub/etc/jupyterhub/jupyterhub_config.py`

You will need to edit the configuration file to make the JupyterLab interface by the default.
Set the following configuration option in your `jupyterhub_config.py` file:

```python
c.Spawner.default_url = '/lab'
```

Further configuration options may be found in the documentation.

### Setup Systemd service

We will setup JupyterHub to run as a system service using Systemd (which is responsible for managing all services and
servers that run on startup in Ubuntu). We will create a service file in a suitable location in the virtualenv folder
and then link it to the system services. First create the folder for the service file:

```sh
sudo mkdir -p /opt/jupyterhub/etc/systemd
```

Then create the following text file using your [favourite editor](https://micro-editor.github.io/) at
```sh
/opt/jupyterhub/etc/systemd/jupyterhub.service
```

Paste the following service unit definition into the file:

```
[Unit]
Description=JupyterHub
After=syslog.target network.target

[Service]
User=root
Environment="PATH=/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/opt/jupyterhub/bin"
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
that was created to install JupyterHub, this is not what we want. So on to part 2

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
echo "deb [arch=amd64] https://repo.anaconda.com/pkgs/misc/debrepo/conda stable main" | sudo tee /etc/apt/sources.list.d/conda.list
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

1 ) Install into the JupyterHub virtualenv - this ensures it overrides the default python version. It will only be visible
to the JupyterHub installation we have just created. This is useful to avoid conda environments appearing where they are not expected.

```sh
sudo /opt/conda/envs/python/bin/python -m ipykernel install --prefix=/opt/jupyterhub/ --name 'python' --display-name "Python (default)"
```

2 ) Install it system-wide by putting it into `/usr/local`. It will be visible to any parallel install of JupyterHub or
JupyterLab, and will persist even if you later delete or modify the JupyterHub installation. This is useful if the kernels
might be used by other services, or if you want to modify the JupyterHub installation independently from the conda environments.

```sh
sudo /opt/conda/envs/python/bin/python -m ipykernel install --prefix /usr/local/ --name 'python' --display-name "Python (default)"
````

### Setting up users' own conda environments

There is relatively little for the administrator to do here, as users will have to set up their own environments using the shell.
On login they should run `conda init` or  `/opt/conda/bin/conda`. The can then use conda to set up their environment,
although they must also install `ipykernel`. Once done, they can enable their kernel using:

```sh
/path/to/kernel/env/bin/python -m ipykernel install --name 'python-my-env' --display-name "Python My Env"
```

This will place the kernel spec into their home folder, where Jupyter will look for it on startup.


## Setting up a reverse proxy

The guide so far results in JupyterHub running on port 8000. It is not generally advisable to run open web services in
this way - instead, use a reverse proxy running on standard HTTP/HTTPS ports.

> **Important**: Be aware of the security implications especially if you are running a server that is accessible from the open internet
> i.e. not protected within an institutional intranet or private home/office network. You should set up a firewall and
> HTTPS encryption, which is outside of the scope of this guide. For HTTPS consider using [LetsEncrypt](https://letsencrypt.org/)
> or setting up a [self-signed certificate](https://www.digitalocean.com/community/tutorials/how-to-create-a-self-signed-ssl-certificate-for-nginx-in-ubuntu-18-04).
> Firewalls may be set up using `ufw` or `firewalld` and combined with `fail2ban`.

### Using Nginx
Nginx is a mature and established web server and reverse proxy and is easy to install using `sudo apt install nginx`.
Details on using Nginx as a reverse proxy can be found elsewhere. Here, we will only outline the additional steps needed
to setup JupyterHub with Nginx and host it at a given URL e.g. `<your-server-ip-or-url>/jupyter`.
This could be useful for example if you are running several services or web pages on the same server.

To achieve this needs a few tweaks to both the JupyterHub configuration and the Nginx config. First, edit the
configuration file `/opt/jupyterhub/etc/jupyterhub/jupyterhub_config.py` and add the line:

```python
c.JupyterHub.bind_url = 'http://:8000/jupyter'
```

where `/jupyter` will be the relative URL of the JupyterHub.

Now Nginx must be configured with a to pass all traffic from `/jupyter` to the the local address `127.0.0.1:8000`.
Add the following snippet to your nginx configuration file (e.g. `/etc/nginx/sites-available/default`).

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

Also add this snippet before the *server* block:

```
map $http_upgrade $connection_upgrade {
        default upgrade;
        '' close;
    }
```

Nginx will not run if there are errors in the configuration, check your configuration using:

```sh
nginx -t
```

If there are no errors, you can restart the Nginx service for the new configuration to take effect.

```sh
sudo systemctl restart nginx.service
```


## Getting started using your new JupyterHub

Once you have setup JupyterHub and Nginx proxy as described, you can browse to your JupyterHub IP or URL
(e.g. if your server IP address is `123.456.789.1` and you decided to host JupyterHub at the `/jupyter` URL, browse
to `123.456.789.1/jupyter`). You will find a login page where you enter your Linux username and password. On login
you will be presented with the JupyterLab interface, with the file browser pane showing the contents of your users'
home directory on the server.
