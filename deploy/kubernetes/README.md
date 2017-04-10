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

**Local Dev. Instance on MacOSX**

The local installation relies on Kube-Solo - a low-overhead Kubernetes setup for MacOS that includes a user-interface for common operations.

1. Clone this github repo to some subdirectory within your HOME directory (for example: /Users/${USER}/code/seqr).


2. Follow these instructions to install Kube-Solo and it's dependencies:
   https://github.com/TheNewNormal/kube-solo-osx/blob/master/README.md#how-to-install-kube-solo

   When the CoreOS VM starts up for the 1st time, it will ask for several parameters. The following settings are recommended:

      Set CoreOS Release Channel:         3)  Stable (recommended)
      Please type VM's RAM size in GBs:   8
      Please type Data disk size in GBs:  20


3. Launch a 'Preset OS Shell' from the Kube-Solo Menu
    
     ![Kube-Solo](https://raw.githubusercontent.com/TheNewNormal/kube-solo-osx/master/kube-solo-osx.png "Kubernetes-Solo")

   This shell environment is preconfigured to have 
 

**Production Instance on Google Cloud**

[Google Container Engine](https://cloud.google.com/container-engine/docs/) makes it easy to create a Kubernetes cluster and then deploy, manage, and scale an application.


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

