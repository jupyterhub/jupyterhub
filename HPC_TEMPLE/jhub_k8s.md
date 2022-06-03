# **Configuring jupyterhub on kubernetes**

### `Step 1 — Installing Docker or configure a Hypervisor`

```console
$ sudo apt update
$ sudo apt install apt-transport-https ca-certificates curl software-properties-common
$ curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
$ sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"
$ apt-cache policy docker-ce
$ sudo apt install docker-ce
```

**sudo systemctl status docker**

```console
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
            -container-ip
            ....
```

_The above indicates that the docker has been successfully installed and running_

### `Step 2 — Installing minikube 1 Node k8s cluster`

```console
$ curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube_latest_amd64.deb
$ sudo dpkg -i minikube_latest_amd64.deb
$ sudo snap install kubectl
```

- Start minikube in docker environment

```console
$ minikube start --driver=docker


😄  minikube v1.25.2 on Ubuntu 20.04
✨  Using the docker driver based on existing profile
👍  Starting control plane node minikube in cluster minikube
🚜  Pulling base image ...
🔄  Restarting existing docker container for "minikube" ...

......

🌟  Enabled addons: storage-provisioner, default-storageclass, dashboard
🏄  Done! kubectl is now configured to use "minikube" cluster and "default" namespace by default

```

- In order to generate the dashboard use **minikube dashboard**
- Few widely used **kubectl commands**

```console
$ kubectl get node
$ kubectl get all
$ kubectl logs <pod_name>

$ kubectl get deployment
$ kubectl delete deployment <deployment_name>
$ kubectl describe deployment <deployment_name>

$ kubectl get service
$ kubectl describe service <service_name>

$ kubectl get replicaset
$ kubectl edit deployment <name>

$ kubectl exec -it <pod_nmae> --bin/bash

```

### `Step 2 — Installing Helm`

- helm is package manager fro kubernetes
- Helm packages ar called **charts**

```console
$ sudo snap install helm

or

$ curl https://raw.githubusercontent.com/helm/helm/HEAD/scripts/get-helm-3 | bash

```

### `Step 2 — Installing jupyterHub`

- After successfully configuring docker, minikube or helm
- Make Helm aware of the JupyterHub Helm chart repository

```console
$ helm repo add jupyterhub https://jupyterhub.github.io/helm-chart/
$ helm repo update

Hang tight while we grab the latest from your chart repositories...
...Successfully got an update from the "jupyterhub" chart repository
Update Complete. ⎈Happy Helming!⎈

$ helm repo list

```

- Download the latest helm charts for jupyterhub from [link-to-Helm-charts-juputerhub](https://jupyterhub.github.io/helm-chart/)

- Using the builtin yaml file we can start jupyterhub

```console
$ helm upgrade <name> jupyterhub/jupyterhub --values=values.yaml
```

```console
$ kubectl describe service hub

Name:              hub
Namespace:         default
Labels:            app=jupyterhub
                   app.kubernetes.io/managed-by=Helm
                   chart=jupyterhub-1.2.0
                   component=hub
                   heritage=Helm
                   release=jhub2
Annotations:       meta.helm.sh/release-name: jhub2
                   meta.helm.sh/release-namespace: default
                   prometheus.io/path: /hub/metrics
                   prometheus.io/port: 8081
                   prometheus.io/scrape: true
Selector:          app=jupyterhub,component=hub,release=jhub2
Type:              ClusterIP
IP Family Policy:  SingleStack
IP Families:       IPv4
IP:                10.110.119.43
IPs:               10.110.119.43
Port:              hub  8081/TCP
TargetPort:        http/TCP
Endpoints:         172.17.0.4:8081
Session Affinity:  None
Events:            <none>

```

- Since we have not configured ingress controller or any other proxy services, we will confine ourself to the use of **minikube tunnel**

```console
$ minikube tunnel
```

- Use the following ip from **service** to access the hub on port 8000/8081

````
Name:              hub
Namespace:         default
Labels:            app=jupyterhub
                   app.kubernetes.io/managed-by=Helm
.....
......
IP:                10.110.119.43
IPs:               10.110.119.43
Port:              hub  8081/TCP
TargetPort:        http/TCP
Endpoints:         172.17.0.4:8081

....
.....

* Getting a shell access to the container

```console
$ kubectl exec -it  <pod_name>  -- bash
````
