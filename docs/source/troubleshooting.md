# Troubleshooting

This document is under active development.

## Networking

If JupyterHub proxy fails to start:

- check if the JupyterHub IP configuration setting is
  ``c.JupyterHub.ip = '*'``; if it is, try ``c.JupyterHub.ip = ''``
- Try starting with ``jupyterhub --ip=0.0.0.0``