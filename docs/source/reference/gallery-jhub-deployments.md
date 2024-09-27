(gallery-of-deployments)=

# A Gallery of JupyterHub Deployments

**A JupyterHub Community Resource**

We've compiled this list of JupyterHub deployments to help the community
see the breadth and growth of JupyterHub's use in education, research, and
high performance computing.

Please submit pull requests to update information or to add new institutions or uses.

## Academic Institutions, Research Labs, and Supercomputer Centers

### University of California Berkeley

- [BIDS - Berkeley Institute for Data Science](https://bids.berkeley.edu/)

- [Data 8](http://data8.org/)

  - [GitHub organization](https://github.com/data-8)

- [NERSC](https://www.nersc.gov/)

  - [Press release on Jupyter and Cori](https://www.nersc.gov/news-publications/nersc-news/nersc-center-news/2016/jupyter-notebooks-will-open-up-new-possibilities-on-nerscs-cori-supercomputer/)
  - [Moving and sharing data](https://www.nersc.gov/assets/Uploads/03-MovingAndSharingData-Cholia.pdf)

- [Research IT](https://research-it.berkeley.edu)
  - [JupyterHub server supports campus research computation](https://research-it.berkeley.edu/blog/17/01/24/free-fully-loaded-jupyterhub-server-supports-campus-research-computation)

### University of California Davis

- [Spinning up multiple Jupyter Notebooks on AWS for a tutorial](https://github.com/mblmicdiv/course2017/blob/HEAD/exercises/sourmash-setup.md)

Although not technically a JupyterHub deployment, this tutorial setup
may be helpful to others in the Jupyter community.

Thank you C. Titus Brown for sharing this with the Software Carpentry
mailing list.

```
* I started a big Amazon machine;
* I installed Docker and built a custom image containing my software of
  interest;
* I ran multiple containers, one connected to port 8000, one on 8001,
  etc. and gave each student a different port;
* students could connect in and use the Terminal program in Jupyter to
  execute commands, and could upload/download files via the Jupyter
  console interface;
* in theory I could have used notebooks too, but for this I didn’t have
  need.

I am aware that JupyterHub can probably do all of this including manage
the containers, but I’m still a bit shy of diving into that; this was
fairly straightforward, gave me disposable containers that were isolated
for each individual student, and worked almost flawlessly.  Should be
easy to do with RStudio too.
```

### Cal Poly San Luis Obispo

- [jupyterhub-deploy-teaching](https://github.com/jupyterhub/jupyterhub-deploy-teaching) based on work by Brian Granger for Cal Poly's Data Science 301 Course

### CERN

[CERN](https://home.cern/), also known as the European Organization for Nuclear Research, is a world-renowned scientific research centre and the home of the Large Hadron Collider (LHC).

Within CERN, there are two noteworthy JupyterHub deployments in operation:

- [SWAN](https://swan.web.cern.ch/swan/), which stands for Service for Web based Analysis, serves as an interactive data analysis platform primarily utilized at CERN.
- [VRE](https://vre-hub.github.io/), which stands for Virtual Research Environment, is an analysis platform developed within the [EOSC Project](https://eoscfuture.eu/) to cater to the needs of scientific communities involved in European projects.

### Chameleon

[Chameleon](https://www.chameleoncloud.org) is a NSF-funded configurable experimental environment for large-scale computer science systems research with [bare metal reconfigurability](https://chameleoncloud.readthedocs.io/en/latest/technical/baremetal.html). Chameleon users utilize JupyterHub to document and reproduce their complex CISE and networking experiments.

- [Shared JupyterHub](https://jupyter.chameleoncloud.org): provides a common "workbench" environment for any Chameleon user.
- [Trovi](https://www.chameleoncloud.org/experiment/share): a sharing portal of experiments, tutorials, and examples, which users can launch as a dedicated isolated environments on Chameleon's JupyterHub.

### Clemson University

- Advanced Computing
  - [Palmetto cluster and JupyterHub](https://citi.sites.clemson.edu/2016/08/18/JupyterHub-for-Palmetto-Cluster.html)

### ETH Zurich

[ETH Zurich](https://ethz.ch/en.html), (Federal Institute of Technology Zurich), is a public research university in Zürich, Switzerland, with focus on science, technology, engineering, and mathematics, although its 16 departments span a variety of disciplines and subjects.

The [Educational Development and Technology](https://ethz.ch/en/the-eth-zurich/organisation/departments/educational-development-and-technology.html) unit provides JupyterHub exclusively for teaching and learning, integrated in the learning management system [Moodle](https://ethz.ch/staffnet/en/teaching/academic-support/it-services-teaching/teaching-applications/moodle-service.html). Each course gets its individually configured JupyterHub environment deployed on a on-premise Kubernetes cluster.

- [ETH JupyterHub](https://ethz.ch/staffnet/en/teaching/academic-support/it-services-teaching/teaching-applications/jupyterhub.html) for teaching and learning

### George Washington University

- [JupyterHub](https://go.gwu.edu/jupyter) with university single-sign-on. Deployed early 2017.

### HTCondor

- [HTCondor Python Bindings Tutorial from HTCondor Week 2017 includes information on their JupyterHub tutorials](https://research.cs.wisc.edu/htcondor/HTCondorWeek2017/presentations/TueBockelman_Python.pdf)

### University of Illinois

- https://datascience.business.illinois.edu (currently down; checked 10/26/22)

### IllustrisTNG Simulation Project

- [JupyterHub/Lab-based analysis platform, part of the TNG public data release](https://www.tng-project.org/data/)

### MIT and Lincoln Labs

- https://supercloud.mit.edu/

### Michigan State University

- [Setting up JupyterHub](https://mediaspace.msu.edu/media/Setting+Up+Your+JupyterHub+Password/1_hgv13aag/11980471)

### University of Minnesota

- [JupyterHub Inside HPC](https://insidehpc.com/tag/jupyterhub/)

### University of Missouri

- https://dsa.missouri.edu/faq/

### Paderborn University

- [Data Science (DICE) group](https://dice-research.org)
  - [nbgraderutils](https://github.com/dice-group/nbgraderutils): Use JupyterHub + nbgrader + iJava kernel for online Java exercises. Used in lecture Statistical Natural Language Processing.

### Penn State University

- [Press release](https://news.psu.edu/story/523093/2018/05/24/new-open-source-web-apps-available-students-and-faculty): "New open-source web apps available for students and faculty"

### University of California San Diego

- San Diego Supercomputer Center - Andrea Zonca

  - [Deploy JupyterHub on a Supercomputer with SSH](https://zonca.github.io/2017/05/jupyterhub-hpc-batchspawner-ssh.html)
  - [Run Jupyterhub on a Supercomputer](https://zonca.github.io/2015/04/jupyterhub-hpc.html)
  - [Deploy JupyterHub on a VM for a Workshop](https://zonca.github.io/2016/04/jupyterhub-sdsc-cloud.html)
  - [Customize your Python environment in Jupyterhub](https://zonca.github.io/2017/02/customize-python-environment-jupyterhub.html)
  - [Jupyterhub deployment on multiple nodes with Docker Swarm](https://zonca.github.io/2016/05/jupyterhub-docker-swarm.html)
  - [Sample deployment of Jupyterhub in HPC on SDSC Comet](https://zonca.github.io/2017/02/sample-deployment-jupyterhub-hpc.html)

- Educational Technology Services - Paul Jamason
  - [datahub.ucsd.edu](https://datahub.ucsd.edu)

### TACC University of Texas

### Texas A&M

- Kristen Thyng - Oceanography
  - [Teaching with JupyterHub and nbgrader](http://kristenthyng.com/blog/2016/09/07/jupyterhub+nbgrader/)

### Elucidata

- What's new in Jupyter Notebooks @[Elucidata](https://elucidata.io/):
  - [Using Jupyter Notebooks with Jupyterhub on GCP, managed by GKE](https://medium.com/elucidata/why-you-should-be-using-a-jupyter-notebook-8385a4ccd93d)

## Service Providers

### AWS

- [Run Jupyter Notebook and JupyterHub on Amazon EMR](https://aws.amazon.com/blogs/big-data/running-jupyter-notebook-and-jupyterhub-on-amazon-emr/)

### Google Cloud Platform

- [Using Tensorflow and JupyterHub in Classrooms](https://cloud.google.com/solutions/using-tensorflow-jupyterhub-classrooms)
- [using-tensorflow-and-jupyterhub blog post](https://opensource.googleblog.com/2016/10/using-tensorflow-and-jupyterhub.html)

### Everware

[Everware](https://github.com/everware) Reproducible and reusable science powered by jupyterhub and docker. Like nbviewer, but executable. CERN, Geneva [website](http://everware.xyz/)

### Microsoft Azure

- [Azure Data Science Virtual Machine release notes](https://docs.microsoft.com/en-us/azure/machine-learning/machine-learning-data-science-linux-dsvm-intro)

### Rackspace Carina

- https://getcarina.com/blog/learning-how-to-whale/
- https://carolynvanslyck.com/talk/carina/jupyterhub/#/ (but carolynvanslyck is currently down; checked 10/26/22)

### Hadoop

- [Deploying JupyterHub on Hadoop](https://jupyterhub-on-hadoop.readthedocs.io)

### Sirepo

- Sirepo is an online Computer-Aided Engineering gateway that contains a JupyterHub instance. Sirepo is provided at no cost for community use, but users must request login access.
- [Sirepo.com](https://www.sirepo.com)
- [Sirepo Jupyter](https://www.sirepo.com/jupyter)

## Miscellaneous

- https://medium.com/@ybarraud/setting-up-jupyterhub-with-sudospawner-and-anaconda-844628c0dbee#.rm3yt87e1
- [Mailing list UT deployment](https://groups.google.com/g/jupyter/c/nkPSEeMr8c0)
- [JupyterHub setup on Centos](https://gist.github.com/johnrc/604971f7d41ebf12370bf5729bf3e0a4)
- [Deploy JupyterHub to Docker Swarm](https://jupyterhub.surge.sh)
- https://www.laketide.com/building-your-lab-part-3/
- https://estrellita.hatenablog.com/entry/2015/07/31/083202
- https://www.walkingrandomly.com/?p=5734
- https://wrdrd.com/docs/consulting/education-technology
- https://bitbucket.org/jackhale/fenics-jupyter
- [LinuxCluster blog](https://linuxcluster.wordpress.com/category/application/jupyterhub/)
- [Spark Cluster on OpenStack with Multi-User Jupyter Notebook](https://arnesund.com/2015/09/21/spark-cluster-on-openstack-with-multi-user-jupyter-notebook/)
