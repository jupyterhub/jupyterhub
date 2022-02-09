docker:
	sudo nvidia-docker build -t jupyterhub . && sudo nvidia-docker rm -f jupyterhub && sudo nvidia-docker run -d -p 8000:8000 --name jupyterhub -v "/ddrive/QABE":"/workspace" jupyterhub && sudo docker exec -it jupyterhub bash
