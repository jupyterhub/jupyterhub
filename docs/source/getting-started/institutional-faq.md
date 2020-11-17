# Institutional FAQ

This page contains common questions from users of JupyterHub,
broken down by their roles within organizations.

## For all

### Is it appropriate for adoption within a larger institutional context?

Yes! JupyterHub has been used at-scale for large pools of users, as well
as complex and high-performance computing. For example, UC Berkeley uses
JupyterHub for its Data Science Education Program courses (serving over
3,000 students). The Pangeo project uses JupyterHub to provide access
to scalable cloud computing with Dask. JupyterHub is stable customizable
to the use-cases of large organizations.

### I keep hearing about Jupyter Notebook, JupyterLab, and now JupyterHub. What’s the difference?

Here is a quick breakdown of these three tools:

* **The Jupyter Notebook** is a document specification (the `.ipynb`) file that interweaves
  narrative text with code cells and their outputs. It is also a graphical interface
  that allows users to edit these documents. There are also several other graphical interfaces
  that allow users to edit the `.ipynb` format (nteract, Jupyter Lab, Google Colab, Kaggle, etc).
* **JupyterLab** is a flexible and extendible user interface for interactive computing. It
  has several extensions that are tailored for using Jupyter Notebooks, as well as extensions
  for other parts of the data science stack.
* **JupyterHub** is an application that manages interactive computing sessions for **multiple users**.
  It also connects them with infrastructure those users wish to access. It can provide
  remote access to Jupyter Notebooks and Jupyter Lab for many people.

## For management

### Briefly, what problem does JupyterHub solve for us?

JupyterHub provides a shared platform for data science and collaboration.
It allows users to utilize familiar data science workflows (such as the scientific python stack,
the R tidyverse, and Jupyter Notebooks) on institutional infrastructure. It also allows administrators
some control over access to resources, security, environments, and authentication.

### Is JupyterHub mature? Why should we trust it?

Yes - the core JupyterHub application recently
reached 1.0 status, and is considered stable and performant for most institutions.
JupyterHub has also been deployed (along with other tools) to work on
scalable infrastructure, large datasets, and high-performance computing.

### Who else uses JupyterHub?

JupyterHub is used at a variety of institutions in academia,
industry, and government research labs. It is most-commonly used by two kinds of groups:

* Small teams (e.g., data science teams, research labs, or collaborative projects) to provide a
  shared resource for interactive computing, collaboration, and analytics.
* Large teams (e.g., a department, a large class, or a large group of remote users) to provide
  access to organizational hardware, data, and analytics environments at scale.

Here are a sample of organizations that use JupyterHub:

* **Universities and colleges**: UC Berkeley, UC San Diego, Cal Poly SLO, Harvard University, University of Chicago,
  University of Oslo, University of Sheffield, Université Paris Sud, University of Versailles
* **Research laboratories**: NASA, NCAR, NOAA, the Large Synoptic Survey Telescope, Brookhaven National Lab,
  Minnesota Supercomputing Institute, ALCF, CERN, Lawrence Livermore National Laboratory
* **Online communities**: Pangeo, Quantopian, mybinder.org, MathHub, Open Humans
* **Computing infrastructure providers**: NERSC, San Diego Supercomputing Center, Compute Canada
* **Companies**: Capital One, SANDVIK code, Globus

See the [Gallery of JupyterHub deployments](../gallery-jhub-deployments.md) for
a more complete list of JupyterHub deployments at institutions.

### How does JupyterHub compare with hosted products, like Google Colaboratory, RStudio.cloud, or Anaconda Enterprise?

JupyterHub puts you in control of your data, infrastructure, and coding environment.
In addition, it is vendor neutral, which reduces lock-in to a particular vendor or service.
JupyterHub provides access to interactive computing environments in the cloud (similar to each of these services).
Compared with the tools above, it is more flexible, more customizable, free, and
gives administrators more control over their setup and hardware.

Because JupyterHub is an open-source, community-driven tool, it can be extended and
modified to fit an institution's needs. It plays nicely with the open source data science
stack, and can serve a variety of computing enviroments, user interfaces, and
computational hardware. It can also be deployed anywhere - on enterprise cloud infrastructure, on
High-Performance-Computing machines, on local hardware, or even on a single laptop, which
is not possible with most other tools for shared interactive computing.

## For IT

### How would I set up JupyterHub on institutional hardware?

That depends on what kind of hardware you've got. JupyterHub is flexible enough to be deployed
on a variety of hardware, including in-room hardware, on-prem clusters, cloud infrastructure,
etc.

The most common way to set up a JupyterHub is to use a JupyterHub distribution, these are pre-configured
and opinionated ways to set up a JupyterHub on particular kinds of infrastructure. The two distributions
that we currently suggest are:

* [Zero to JupyterHub for Kubernetes](https://z2jh.jupyter.org) is a scalable JupyterHub deployment and
  guide that runs on Kubernetes. Better for larger or dynamic user groups (50-10,000) or more complex
  compute/data needs.
* [The Littlest JupyterHub](https://tljh.jupyter.org) is a lightweight JupyterHub that runs on a single
  single machine (in the cloud or under your desk). Better for smaller usergroups (4-80) or more
  lightweight computational resources.


### Does JupyterHub run well in the cloud?

Yes - most deployments of JupyterHub are run via cloud infrastructure and on a variety of cloud providers.
Depending on the distribution of JupyterHub that you'd like to use, you can also connect your JupyterHub
deployment with a number of other cloud-native services so that users have access to other resources from
their interactive computing sessions.

For example, if you use the [Zero to JupyterHub for Kubernetes](https://z2jh.jupyter.org) distribution,
you'll be able to utilize container-based workflows of other technologies such as the [dask-kubernetes](https://kubernetes.dask.org/en/latest/)
project for distributed computing.

The Z2JH Helm Chart also has some functionality built in for auto-scaling your cluster up and down
as more resources are needed - allowing you to utilize the benefits of a flexible cloud-based deployment.

### Is JupyterHub secure?

The short answer: yes. JupyterHub as a standalone application has been battle-tested at an institutional
level for several years, and makes a number of "default" security decisions that are reasonable for most
users.

* For security considerations in the base JupyterHub application,
  [see the JupyterHub security page](https://jupyterhub.readthedocs.io/en/stable/reference/websecurity.html)
* For security considerations when deploying JupyterHub on Kubernetes, see the
  [JupyterHub on Kubernetes security page](https://zero-to-jupyterhub.readthedocs.io/en/latest/security.html).

The longer answer: it depends on your deployment. Because JupyterHub is very flexible, it can be used
in a variety of deployment setups. This often entails connecting your JupyterHub to **other** infrastructure
(such as a [Dask Gateway service](https://gateway.dask.org/)). There are many security decisions to be made
in these cases, and the security of your JupyterHub deployment will often depend on these decisions.

If you are worried about security, don't hesitate to reach out to the JupyterHub community in the
[Jupyter Community Forum](https://discourse.jupyter.org/c/jupyterhub). This community of practice has many
individuals with experience running secure JupyterHub deployments.


### Does JupyterHub provide computing or data infrastructure?

No - JupyterHub manages user sessions and can *control* computing infrastructure, but it does not provide these
things itself. You are expected to run JupyterHub on your own infrastructure (local or in the cloud). Moreover,
JupyterHub has no internal concept of "data", but is designed to be able to communicate with data repositories
(again, either locally or remotely) for use within interactive computing sessions.


### How do I manage users?

JupyterHub offers a few options for managing your users. Upon setting up a JupyterHub, you can choose what
kind of **authentication** you'd like to use. For example, you can have users sign up with an institutional
email address, or choose a username / password when they first log-in, or offload authentication onto
another service such as an organization's OAuth.

The users of a JupyterHub are stored locally, and can be modified manually by an administrator of the JupyterHub.
Moreover, the *active* users on a JupyterHub can be found on the administrator's page. This page
gives you the abiltiy to stop or restart kernels, inspect user filesystems, and even take over user
sessions to assist them with debugging.

### How do I manage software environments?

A key benefit of JupyterHub is the ability for an administrator to define the environment(s) that users
have access to. There are many ways to do this, depending on what kind of infrastructure you're using for
your JupyterHub.

For example, **The Littlest JupyterHub** runs on a single VM. In this case, the administrator defines
an environment by installing packages to a shared folder that exists on the path of all users. The
**JupyterHub for Kubernetes** deployment uses Docker images to define environments. You can create your
own list of Docker images that users can select from, and can also control things like the amount of
RAM available to users, or the types of machines that their sessions will use in the cloud.

### How does JupyterHub manage computational resources?

For interactive computing sessions, JupyterHub controls computational resources via a **spawner**.
Spawners define how a new user session is created, and are customized for particular kinds of
infrastructure. For example, the KubeSpawner knows how to control a Kubernetes deployment
to create new pods when users log in.

For more sophisticated computational resources (like distributed computing), JupyterHub can
connect with other infrastructure tools (like Dask or Spark). This allows users to control
scalable or high-performance resources from within their JupyterHub sessions. The logic of
how those resources are controlled is taken care of by the non-JupyterHub application.


### Can JupyterHub be used with my high-performance computing resources?

Yes - JupyterHub can provide access to many kinds of computing infrastructure.
Especially when combined with other open-source schedulers such as Dask, you can manage fairly
complex computing infrastructure from the interactive sessions of a JupyterHub. For example
[see the Dask HPC page](https://docs.dask.org/en/latest/setup/hpc.html).

### How much resources do user sessions take?

This is highly configurable by the administrator. If you wish for your users to have simple
data analytics environments for prototyping and light data exploring, you can restrict their
memory and CPU based on the resources that you have available. If you'd like your JupyterHub
to serve as a gateway to high-performance compute or data resources, you may increase the
resources available on user machines, or connect them with computing infrastructure elsewhere.

### Can I customize the look and feel of a JupyterHub?

JupyterHub provides some customization of the graphics displayed to users. The most common
modification is to add custom branding to the JupyterHub login page, loading pages, and
various elements that persist across all pages (such as headers).

## For Technical Leads

### Will JupyterHub “just work” with our team's interactive computing setup?

Depending on the complexity of your setup, you'll have different experiences with "out of the box"
distributions of JupyterHub. If all of the resources you need will fit on a single VM, then
[The Littlest JupyterHub](https://tljh.jupyter.org) should get you up-and-running within
a half day or so. For more complex setups, such as scalable Kubernetes clusters or access
to high-performance computing and data, it will require more time and expertise with
the technologies your JupyterHub will use (e.g., dev-ops knowledge with cloud computing).

In general, the base JupyterHub deployment is not the bottleneck for setup, it is connecting
your JupyterHub with the various services and tools that you wish to provide to your users.


### How well does JupyterHub scale? What are JupyterHub's limitations?

JupyterHub works well at both a small scale (e.g., a single VM or machine) as well as a
high scale (e.g., a scalable Kubernetes cluster). It can be used for teams as small a 2, and
for user bases as large as 10,000. The scalability of JupyterHub largely depends on the
infrastructure on which it is deployed. JupyterHub has been designed to be lightweight and
flexible, so you can tailor your JupyterHub deployment to your needs.


### Is JupyterHub resilient? What happens when a machine goes down?

For JupyterHubs that are deployed in a containerized environment (e.g., Kubernetes), it is
possible to configure the JupyterHub to be fairly resistant to failures in the system.
For example, if JupyterHub fails, then user sessions will not be affected (though new
users will not be able to log in). When a JupyterHub process is restarted, it should
seamlessly connect with the user database and the system will return to normal.
Again, the details of your JupyterHub deployment (e.g., whether it's deployed on a scalable cluster)
will affect the resiliency of the deployment.

### What interfaces does JupyterHub support?

Out of the box, JupyterHub supports a variety of popular data science interfaces for user sessions,
such as JupyterLab, Jupyter Notebooks, and RStudio. Any interface that can be served
via a web address can be served with a JupyterHub (with the right setup).

### Does JupyterHub make it easier for our team to collaborate?

JupyterHub provides a standardized environment and access to shared resources for your teams.
This greatly reduces the cost associated with sharing analyses and content with other team
members, and makes it easier to collaborate and build off of one another's ideas. Combined with
access to high-performance computing and data, JupyterHub provides a common resource to
amplify your team's ability to prototype their analyses, scale them to larger data, and then
share their results with one another.

JupyterHub also provides a computational framework to share computational narratives between
different levels of an organization. For example, data scientists can share Jupyter Notebooks
rendered as [voila dashboards](https://voila.readthedocs.io/en/stable/) with those who are not
familiar with programming, or create publicly-available interactive analyses to allow others to
interact with your work.

### Can I use JupyterHub with R/RStudio or other languages and environments?

Yes, Jupyter is a polyglot project, and there are over 40 community-provided kernels for a variety
of languages (the most common being Python, Julia, and R). You can also use a JupyterHub to provide
access to other interfaces, such as RStudio, that provide their own access to a language kernel.
