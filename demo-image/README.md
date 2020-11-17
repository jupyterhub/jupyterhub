## Demo Dockerfile

This is a demo JupyterHub Docker image to help you get a quick overview of what
JupyterHub is and how it works.

It uses the SimpleLocalProcessSpawner to spawn new user servers and
DummyAuthenticator for authentication.
The DummyAuthenticator allows you to log in with any username & password and the
SimpleLocalProcessSpawner allows starting servers without having to create a
local user for each JupyterHub user.

### Important!

This should only be used for demo or testing purposes!
It shouldn't be used as a base image to build on.

### Try it
1. `cd` to the root of your jupyterhub repo.

2. Build the demo image with `docker build -t jupyterhub-demo demo-image`. 

3. Run the demo image with `docker run -d -p 8000:8000 jupyterhub-demo`.

4. Visit http://localhost:8000 and login with any username and password
5. Happy demo-ing :tada:!
