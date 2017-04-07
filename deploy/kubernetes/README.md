This README describes how to install a stand-alone seqr server, and includes steps for setting up
both a local development instance and a cloud-based production instance.
Both local and cloud-based deployments use Kubernetes - an open-source system for automating deployment,
scaling, and management of containerized applications.

Overview
--------

seqr consists of the following components or micro-services:
- seqr - the main client-server application - developed using javascript + react.js on the client-side and python + django on the server-side
- phenotips - 3rd-party web-based application for entering structured phenotype information
- matchbox - a service that encapsulates communication with the Match Maker Exchange network
- postgres - SQL database used by seqr and phenotips to store metadata and small reference datasets (eg. OMIM, clinvar)
- mongo - NoSQL database used to store large variant datasets and reference data
- nginx - http server used as the main gateway between seqr and the internet.


Prerequisites
-------------

Before deploying seqr, you must first create a Kubernetes cluster that will host the deployed seqr components, 
and the sections below describe how do this in different environments. 

**Local Dev. Instance on MacOSX**

1. Follow these instructions to install Kube-Solo and it's dependencies:  
   https://github.com/TheNewNormal/kube-solo-osx/blob/master/README.md#how-to-install-kube-solo

   When the CoreOS VM starts up for the 1st time, it will ask for several parameters. The following settings should work well:
     ```
     Set CoreOS Release Channel:         3)  Stable (recommended)  
     Please type VM's RAM size in GBs:   8  
     Please type Data disk size in GBs:  20
     ```

2. Launch a 'Preset OS Shell'
3.

For the development instance, you should also clone a copy of the seqr source code directly onto your
development machine.

1.
* seqr production instance

...


Installation
------------

Recommended approach:
 Kubernetes - 
    - local development - currently there are two popular ways to set up a local kubernetes cluster:
        `minicube` is the official 
                  rely on new low-overhead virtualization features built in to linux and the latest versions of MacOSX,
                    
                  - `minicube` - is the officially-supported approach for local installs. It uses 
                  
 

Other ways to install seqr:

 - `scripts` - Install all dependencies, databases and code directly onto the machine. 
   The bash scripts in `deploy/scripts` can be used as examples.  
   *Pro:* doesn't require docker or kubernetes  
   *Con:* each seqr component must be installed, configured and started manually. Also, some components
     may run into unexpected conflicts with existing software or python library versions on the machine.    
 - `docker` -  if [docker](https://docs.docker.com/docker-for-mac/) is installed on your machine, 
     the Dockerfiles under `deploy/docker` can be used to create containers for all seqr components.  
   *Pro:*  standardized installation of each component, isolated from other software.   
   *Con:*  containers must then be manually linked together to enable communication (eg. allowing the
      django/python container to connect to the database container, etc). Any subsequent vertical or horizontal 
      scaling must also be done manually.
 - `kubernetes`- recommend approach 
    *Pro:* kubernetes allows groups of docker containers to be deployed together in an automated, standardized way 
        and deals with a range of issues related to managing these deployments. For example, it allows a single
        deployment process and set of scripts to be reused essentially without modification both for production environments 
        (such as Google or AWS clouds) and for local or dev deployments (such as a virtualized kubernetes cluster 
    running locally on your dev machine).  
    *Con:*  requires learning about a number of new technologies, including docker.
 

https://kubernetes.io/docs/tutorials/stateless-application/hello-minikube/


Kubernetes Resources
--------------------

- Official Kuberentes User Guide:  https://kubernetes.io/docs/user-guide/
- 15 Kubernetes Features in 15 Minutes: https://www.youtube.com/watch?v=o85VR90RGNQ
- Kubernetes: Up and Running: https://www.safaribooksonline.com/library/view/kubernetes-up-and/9781491935668/
- The Children's Illustrated Guide to Kubernetes: https://deis.com/blog/2016/kubernetes-illustrated-guide/

