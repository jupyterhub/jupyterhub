# Installing jupyterhub on docker

### `Step 1 — Installing Docker`
```
$ sudo apt update
$ sudo apt install apt-transport-https ca-certificates curl software-properties-common
$ curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
$ sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"
$ apt-cache policy docker-ce
$ sudo apt install docker-ce
```
**sudo systemctl status docker**
```
● docker.service - Docker Application Container Engine
     Loaded: loaded (/lib/systemd/system/docker.service; enabled; vendor preset: enabled)
     Active: active (running) since Sat 2022-05-21 17:55:54 CEST; 2h 36min ago
TriggeredBy: ● docker.socket
       Docs: https://docs.docker.com
   Main PID: 4427 (dockerd)
      Tasks: 56
     Memory: 119.4M
     CGroup: /system.slice/docker.service
             ├─  4427 /usr/bin/dockerd -H fd:// --containerd=/run/containerd/containerd.sock
             ├─  4814 /usr/bin/docker-proxy -proto tcp -host-ip 0.0.0.0 -host-port 9443 -container-ip 1>
             ├─  4820 /usr/bin/docker-proxy -proto tcp -host-ip :: -host-port 9443 -container-ip 172.17>
             ├─  4836 /usr/bin/docker-proxy -proto tcp -host-ip 0.0.0.0 -host-port 8000 -container-ip 1>
             ├─  4843 /usr/bin/docker-proxy -proto tcp -host-ip :: -host-port 8000 -container-ip 172.17>
             ├─177440 /usr/bin/docker-proxy -proto tcp -host-ip 0.0.0.0 -host-port 8001 -container-ip 1>
             └─177446 /usr/bin/docker-proxy -proto tcp -host-ip :: -host-port 8001 -container-ip
```

*The above indicates that the docker has been successfully  installed and running*

### `Step 2 — Install Portainer with Docker`
```
$ docker volume create portainer_data
$ docker run -d -p 9000:8000 -p 9443:9443 --name portainer \
    --restart=always \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v portainer_data:/data \
    portainer/portainer-ce:2.9.3
```
**docker ps**
```
CONTAINER ID   IMAGE                          COMMAND        CREATED          STATUS          PORTS                                                                                            NAMES
05c417c7ab1c   jupyterhub/jupyterhub          "jupyterhub"   18 minutes ago   Up 18 minutes   0.0.0.0:8001->8000/tcp, :::8001->8000/tcp                                                        jupyterhub
0a6533d8fcc2   portainer/portainer-ce:2.9.3   "/portainer"   8 hours ago      Up 3 hours      0.0.0.0:8000->8000/tcp, :::8000->8000/tcp, 0.0.0.0:9443->9443/tcp, :::9443->9443/tcp, 9000/tcp   portainer

```
**https://localhost:9443**
### `Step 3 — Configuring Jupyterhub on docker`

* We will pull the latest image from https://hub.docker.com/r/jupyterhub/jupyterhub/#docker 

* Refer to the documentation for installation and configuration 

```
$ docker pull jupyterhub/jupyterhub
$ docker run -p 8000:8000 -d --name jupyterhub jupyterhub/jupyterhub jupyterhub
```
*This command will create a container named jupyterhub that you can stop and resume with docker stop/start.The Hub service will be listening on all interfaces at port 8001, which makes this a good choice for testing JupyterHub on your desktop or laptop.*

*To create system user in the container*
```
$ docker exec -it jupyterhub bash
$ adduser admin
$ npm install -g configurable-http-proxy
$ python3 -m pip install jupyterlab notebook
```
### `Step 4 — Config file in Docker`
```
$ docker ps
$ docker exec -u 0 -it CONTAINER-ID /bin/bash
```
