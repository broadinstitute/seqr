This README describes how to set up either a local or a cloud-based seqr server using [Kubernetes](https://kubernetes.io/).

Overview
--------

seqr consists of the following components or micro-services:
- seqr - the main client-server application - javascript + react.js on the client-side, python + django on the server-side
- postgres - SQL database used by seqr and phenotips to store metadata and small reference datasets (eg. OMIM, clinvar)
- mongo - NoSQL database used to store large variant datasets and reference data
- phenotips - 3rd-party web-based tool for entering structured phenotype information
- matchbox - a service that encapsulates communication with the Match Maker Exchange network
- nginx - http server used as the main gateway between seqr and the internet.


Prerequisites
-------------

Before deploying seqr, you must first create a Kubernetes cluster that will host the above components:

1. Install kubectl: 
   https://kubernetes.io/docs/tasks/kubectl/install/

**Local Dev. Instance on MacOSX**

The local installation relies on Kube-Solo - a low-overhead Kubernetes setup for MacOS.

1. Install CoreOS - the virtual machine that will run Kubernetes:

   a. Install a dependency:  `brew install libev`
   b. Install the latest DMG from https://github.com/TheNewNormal/corectl.app/releases   
   
2. Install Kube-Solo:
   https://github.com/TheNewNormal/kube-solo-osx/releases

3. Initialize:

   ![Kube-Solo](https://raw.githubusercontent.com/TheNewNormal/kube-solo-osx/master/kube-solo-osx.png "Kubernetes-Solo")

   a. When launching Kube-Solo for the 1st time, click on `Setup > Initial Setup of Kube-Solo VM`
      It will open an iTerm2 shell and ask for several inputs. The following settings are recommended:

         Set CoreOS Release Channel:         3) Stable (recommended)
         Please type VM's RAM size in GBs:   8
         Please type Data disk size in GBs:  20
 
   b. After this initial setup, you can just use `Preset OS Shell` to open a new terminal where docker and kubectl are preconfigured to use the local kubernetes cluster. 
   
3. Clone this github repo to some subdirectory within your HOME directory (for example: /Users/${USER}/code/seqr).


**Production Instance on Google Cloud**

[Google Container Engine](https://cloud.google.com/container-engine/docs/) makes it easy to create a Kubernetes cluster and then deploy, manage, and scale an application.


1. Install Docker for MacOSX: 
   https://getcarina.com/docs/tutorials/docker-install-mac/

   It will be used to build docker images before pushing them to your private repo on Google Container Engine.


Installing and Managing Seqr
----------------------------

To deploy all seqr components to your Kubernetes environment, 

    ./seqrctl deploy-and-load {label}   # label can be 'local' or 'gcloud'


The `./seqrctl` script provides subcommands for deploying seqr components, loading reference and example datasets, and
 performing common development and troubleshooting steps. It supports these additional commands:
         
      deploy-and-load  {local,gcloud}                        # End-to-end deployment - deploys all seqr components and loads reference data + an example project
      deploy {postgres,phenotips,mongo,seqr,nginx,matchbox} {local,gcloud}  # Deploy one or more components
      load  {reference-data,example-project}                 #  Load reference or example datasets to initialize seqr
      logs {postgres,phenotips,mongo,seqr,nginx,matchbox}    # show logs for one or more components
      forward {postgres,phenotips,mongo,seqr,nginx,matchbox} # start port-forwarding for service(s) running in the given component container(s), allowing connections via localhost
      connect-to {postgres,phenotips,mongo,seqr,nginx,matchbox}  # simultaneously starts both port-forwarding and showing logs
      shell {postgres,phenotips,mongo,seqr,nginx,matchbox}   # open a bash shell inside one of the component containers
      create-user     
      status
      

Kubernetes Resources
--------------------

- Official Kuberentes User Guide:  https://kubernetes.io/docs/user-guide/
- 15 Kubernetes Features in 15 Minutes: https://www.youtube.com/watch?v=o85VR90RGNQ
- Kubernetes: Up and Running: https://www.safaribooksonline.com/library/view/kubernetes-up-and/9781491935668/
- The Children's Illustrated Guide to Kubernetes: https://deis.com/blog/2016/kubernetes-illustrated-guide/

