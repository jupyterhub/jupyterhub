# Automatic HTTPS Terminator

This directory has Kubernetes objects for automatic Let's Encrypt Support.
When enabled, we create a new deployment object that has an nginx-ingress
and kube-lego container in it. This is responsible for requesting,
storing and renewing certificates as needed from Let's Encrypt.

The only change required outside of this directory is in the `proxy-public`
service, which targets different hubs based on automatic HTTPS status.