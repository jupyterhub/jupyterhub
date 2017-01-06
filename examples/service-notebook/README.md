# Running a shared notebook as a service

This directory contains two examples of running a shared notebook server as a service,
one as a 'managed' service, and one as an external service with supervisor.

A single-user notebook server is run as a service,
and uses groups to authenticate a collection of users with the Hub.

These examples require jupyterhub >= 0.7.2.

