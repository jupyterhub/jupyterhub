# SAIEP UI Setup

## Requirements
- Python 3.12
- Node.js 20 + npm

## Installation
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
pip install jupyterlab notebook Pillow
sudo npm install -g configurable-http-proxy
```

## Apply SAIEP Branding
```bash
bash setup_ui.sh
```

## Start JupyterHub
```bash
sudo venv/bin/jupyterhub -f jupyterhub_config.py
```

## Access
Open your browser at `http://<server-ip>:8000`
