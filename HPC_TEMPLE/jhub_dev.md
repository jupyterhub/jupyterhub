# Installing jupyterhub on docker

### `Step 1 — Installing little jhub`
```
$ sudo apt install python3 python3-dev git curl
$ curl -L https://tljh.jupyter.org/bootstrap.py | sudo -E python3 - --admin admin_name

```
### `Step 2 — Installing jhub in dev mode`
```
$ sudo apt install python3 python3-dev git curl
$ git clone https://github.com/jupyterhub/jupyterhub
$ git clone https://github.com/mhasan49/jupyterhub.git
$ cd jupyterhub
$ sudo npm install -g configurable-http-proxy
$ python3 -m pip install -r dev-requirements.txt
$ python3 -m pip install -r requirements.txt
$ python3 -m pip install --editable .
$ jupyterhub -f testing/jupyterhub_config.py

```

