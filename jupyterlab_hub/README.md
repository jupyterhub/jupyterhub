# jupyterlab_hub

JupyterLab extension intergating JupyterHub


## Prerequisites

* JupyterLab 0.3.0 or later

## Installation

To install using pip:

```bash
pip install jupyterlab_hub
jupyter labextension install --py --sys-prefix jupyterlab_hub
jupyter labextension enable --py --sys-prefix jupyterlab_hub
```

## Development

For a development install (requires npm version 4 or later), do the following in the repository directory:

```bash
npm install
pip install -e .
jupyter labextension install --symlink --py --sys-prefix jupyterlab_hub
jupyter labextension enable --py --sys-prefix jupyterlab_hub
```

To rebuild the extension bundle:

```bash
npm run build
```

