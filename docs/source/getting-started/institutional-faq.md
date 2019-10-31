# Institutional FAQ

This page contains common questions from users of JupyterHub,
broken down by their roles within organizations.

# For all

## Is appropriate for adoption within a larger institutional context?

Yes! JupyterHub has been used at-scale for large pools of users, as well
as complex and high-performance computing. For example, UC Berkeley uses
JupyterHub for its Data Science Education Program courses (serving over
3,000 students). The Pangeo project uses JupyterHub to provide access
to scalable cloud computing with Dask. JupyterHub is stable customizable
to the use-cases of large organizations.

## I keep hearing about Jupyter Notebook, JupyterLab, and now JupyterHub. What’s the difference?

Here is a quick breakdown of these three tools:

* **The Jupyter Notebook** is a document specification (the `.ipynb`) file that interweaves
  narrative text with code cells and their outputs. It is also a graphical interface
  that allows users to edit these documents
* **JupyterLab** is a flexible and extendible user interface for interactive computing. It
  has several extensions that are tailored for using Jupyter Notebooks, as well as extensions
  for other parts of the data science stack.
* **JupyterHub** is an application that can manage **multiple users** with interactive computing
  sessions, as well as connect with infrastructure those users wish to access. It can provide
  remote access to Jupyter Notebooks and Jupyter Lab for many people, and can connect them with
  other compute infrastructure.

# For management

## Briefly, what problem does JupyterHub solve for us?

JupyterHub provides a shared platform for data science and collaboration.
It allows users to utilize familiar data science workflows (such as the scientific python stack,
the R tidyverse, and Jupyter Notebooks) on institutional infrastructure. It also allows administrators
some control over access to resources, security, authentication, and user identity.

## Is JupyterHub mature? Why should we trust it?

Yes - the core JupyterHub application recently
reached 1.0 status, and is considered stable and performant for most institutions.
JupyterHub has also been deployed (along with other tools) to work on
scalable infrastructure, large datasets, and high-performance computing.

## Who else uses JupyterHub?

JupyterHub has been used at a variety of institutions in academia,
industry, and governmental research labs. These include:

* <list of orgs>

## How does JupyterHub compare with hosted products, like Google Colaboratory, RStudio.cloud, or Anaconda Enterprise?

Like the tools listed above, JupyterHub provides access to interactive computing
environments in the cloud. However, JupyterHub is more flexible, more customizable,
free, and gives administrators more control over their setup and hardware.

Because JupyterHub is an open-source, community-driven tool, it can be extended and
modified to fit an institution's needs. It plays nicely with the open source data science
stack, and can serve a variety of computing enviroments, user interfaces, and
computational hardware.

Finally, JupyterHub can be deployed anywhere - on enterprise cloud infrastructure, on
High-Performance-Computing machines, on local hardware, or even on a single laptop.

# For IT

## How would I set up JupyterHub on institutional hardware?

That depends on what kind of hardware you've got. JupyterHub is flexible enough to be deployed
on a variety of hardware, including in-room hardware, on-prem clusters, cloud infrastructure,
etc.

The most common way to set up a JupyterHub us to use a JupyterHub distribution, these are pre-configured
and opinionated ways to set up a JupyterHub on particular kinds of infrastructure. The two distributions
that we currently suggest are:

* [Zero to JupyterHub for Kubernetes](https://z2jh.jupyter.org) is a scalable JupyterHub deployment and
  guide that runs on Kubernetes. Better for larger or dynamic user groups (50-10,000) or more complex
  compute/data needs.
* [The Littlest JupyterHub](https://tljh.jupyter.org) is a lightweight JupyterHub that runs on a single
  VM in the cloud. Better for smaller usergroups (4-80) or more lightweight computational resources.


## Does JupyterHub run well in the cloud?

Yes - most deployments of JupyterHub are run via cloud infrastructure and on a variety of cloud providers.
Depending on the distribution of JupyterHub that you'd like to use, you can also connect your JupyterHub
deployment with a number of other cloud-native services so that users have access to other resources from
their interactive computing sessions.

For example, if you use the [Zero to JupyterHub for Kubernetes](https://z2jh.jupyter.org) distribution,
you'll be able to utilize container-based workflows of other technologies such as the [dask-kubernetes](https://kubernetes.dask.org/en/latest/)
project for distributed computing.

The Z2JH Helm Chart also has some functionality built in for auto-scaling your cluster up and down
as more resources are needed - allowing you to utilize the benefits of a flexible cloud-based deployment.

## Is JupyterHub secure?

The short answer: yes. JupyterHub as a standalone application has been battle-tested at an institutional
level for several years, and makes a number of "default" security decisions that are reasonable for most
users.

The longer answer: it depends on your deployment. Because JupyterHub is very flexible, it can be used
in a variety of deployment setups. This often entails connecting your JupyterHub to **other** infrastructure
(such as a [Dask Gateway service](https://gateway.dask.org/)). There are many security decisions to be made
in these cases, and the security of your JupyterHub deployment will often depend on these decisions.

If you are worried about security, don't hesitate to reach out to the JupyterHub community in the
[Jupyter Community Forum](https://discourse.jupyter.org/c/jupyterhub). This community of practice has many
individuals with experience running secure JupyterHub deployments.


## Does JupyterHub provide computing or data infrastructure?

No - JupyterHub manages user sessions and can *control* computing infrastructure, but it does not provide these
things itself. You are expected to run JupyterHub on your own infrastructure (local or in the cloud). Moreover,
JupyterHub has no internal concept of "data", but is designed to be able to communicate with data repositories
(again, either locally or remotely) for use within interactive computing sessions.


## How do I manage users?



## How do I manage software environments?

## How does JupyterHub manage computational resources?

## Can JupyterHub be used with my high-performance computing resources?

## How much resources do user sessions take?

## Can I customize the look and feel of a JupyterHub?
* Branding notebook server / jupyter lab. Custom error pages / support and help pages


# For Technical Leads

## Will JupyterHub “just work” with our team's interactive computing setup?

## How well does JupyterHub scale? What are JupyterHub's limitations?

## Will our team have to re-write their code when they want to scale to high-performance compute?

## Is JupyterHub resilient? What happens when a machine goes down?

## What interfaces does JupyterHub support?

## Does JupyterHub make it easier for our team to collaborate?

## Can I use JupyterHub with R/RStudio or other languages and environments?