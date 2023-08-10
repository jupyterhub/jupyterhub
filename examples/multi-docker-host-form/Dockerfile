FROM jupyterhub/jupyterhub:latest

RUN python3 -m pip install --no-cache-dir dockerspawner

CMD ["jupyterhub", "-f", "/srv/jupyterhub/jupyterhub_config.py"]