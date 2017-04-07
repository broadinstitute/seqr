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


Kubernetes Resources
--------------------

- Official Kuberentes User Guide:  https://kubernetes.io/docs/user-guide/
- 15 Kubernetes Features in 15 Minutes: https://www.youtube.com/watch?v=o85VR90RGNQ
- Kubernetes: Up and Running: https://www.safaribooksonline.com/library/view/kubernetes-up-and/9781491935668/
- The Children's Illustrated Guide to Kubernetes: https://deis.com/blog/2016/kubernetes-illustrated-guide/

