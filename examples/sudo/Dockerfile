# example showing sudo config
# docker run -it -p 9000:8000 jupyter/jupyterhub-sudo

FROM jupyter/jupyterhub

MAINTAINER Jupyter Project <ipython-dev@scipy.org>

# fix permissions on sudo executable (how did this get messed up?)
RUN chmod 4755 /usr/bin/sudo

# add the rhea user, who will run the server
# she needs to be in the shadow group in order to access the PAM service
RUN useradd -m -G shadow -p $(openssl passwd -1 rhea) rhea

# Give rhea passwordless sudo access to run the single-user servers on behalf of users:
ADD sudoers /tmp/sudoers
RUN cat /tmp/sudoers >> /etc/sudoers
RUN rm /tmp/sudoers

# add the regular users
RUN for name in io ganymede; do useradd -m -p $(openssl passwd -1 $name) $name; done

# make the working dir owned by rhea, so she can create the state database
RUN chown rhea .

# run the server as rhea instead of root
USER rhea
