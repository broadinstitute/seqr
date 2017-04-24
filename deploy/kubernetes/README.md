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

Make sure you have python2.7 installed, and on your `PATH`.

Clone this github repo to a subdirectory of your `HOME` directory (for example: ~/code/seqr), and install python dependencies:  

       cd ~/code
       git clone https://github.com/macarthur-lab/seqr.git
       cd seqr/deploy/kubernetes
       pip install -r requirements.txt

You must also create a Kubernetes cluster that will host the micro-services that make up seqr - as follows:

**Local Dev. Instance on MacOSX**

The local installation relies on Kube-Solo - a low-overhead Kubernetes setup for MacOS.

1. Install CoreOS - the virtual machine that will run Kubernetes:

   a. Install a dependency:  `brew install libev`  
   b. Install the latest DMG from https://github.com/TheNewNormal/corectl.app/releases   

   `WARNING: ` Being on a VPN connection may cause errors during CoreOS install steps that need to download components from the web.
   The solution is to disconnect from the VPN.

2. Install Kube-Solo: https://github.com/TheNewNormal/kube-solo-osx/releases

3. Install kubectl: https://kubernetes.io/docs/tasks/kubectl/install/

4. Initialize:

   ![Kube-Solo](https://raw.githubusercontent.com/TheNewNormal/kube-solo-osx/master/kube-solo-osx.png "Kubernetes-Solo")

   a. When launching Kube-Solo for the 1st time, click on `Setup > Initial Setup of Kube-Solo VM`
      It will open an iTerm2 shell and ask for several inputs. The following settings are recommended:

         Set CoreOS Release Channel:         3) Stable (recommended)
         Please type VM's RAM size in GBs:   8
         Please type Data disk size in GBs:  20
 
   b. After this initial setup, you can just click `Preset OS Shell` to open a new terminal where docker and kubectl are preconfigured to use the local kubernetes cluster. 


5.  **Trouble-shooting:** If your computer goes to sleep or reboots, the CoreOS / Kube-Solo VM may become unresponsive, requiring it to be rebooted (or possibly even reinitialized)

    For some reason,

            The following steps fail if you're connected to a VPN

    so be sure to disconnect before proceeding.

    You can click `Halt` and then `Up` in the Kube-Solo menu to shut-down and then restart the VM.
    This typically resolves most issues. If Halt takes a long time, running `pkill kube` on the command-line may help.
    Kubernetes and seqr components will automatically start up when the VM restarts.

    If issues persist, you can delete and reinitialize the Kube-Solo VM by Halting it and then running `rm -rf ~/kube-solo`.
    If you then click `Up` in the Kube-Solo menu, it will reinitialize the VM from scratch.


**Production Instance on Google Cloud**

[Google Container Engine](https://cloud.google.com/container-engine/docs/) makes it easy to create a Kubernetes cluster and then deploy, manage, and scale an application. The following steps are necessary before `./seqrctl` can be used to deploy to a Google Container Engine cluster:

1. Install Docker for MacOSX:  
   https://getcarina.com/docs/tutorials/docker-install-mac/

   It will be used to build docker images before pushing them to your private repo on Google Container Engine.

2. Install kubectl: https://kubernetes.io/docs/tasks/kubectl/install/


Configuration
-------------

The seqr installation process described below should produce a working instance with default settings.  
However, for best results, you may want to first adjust the following parameters.  
*NOTE:* These file paths are relative to `~/code/seqr/deploy/kubernetes`  

`secrets/*/*.*` - these directories contain private or sensitive settings for each seqr component - such as passwords, tockens, and SSL keys. Changes to these files should not be committed to github. Instead they will be safely injected into relevant components during deployment using Kubernetes secrets-related features.    
    
     secrets/*/nginx/tls.* - SSL certificates to enable HTTPS
     secrets/*/postgres/postgres.* - the postgres database will be configured to require this username and password. The database isn't visible outside the Kubernetes internal network, so these are not the primary level of security.
     secrets/*/seqr/omim_key - this key can be obtained by filling out a form: https://omim.org/api 
    
    
`config/*-settings.yaml` - these files contain non-private settings for each type of deployment, and can be customized for local deployments (particularly gcloud-settings.yaml).  


Installing and Managing Seqr
----------------------------

To deploy all seqr components to your Kubernetes environment, 

    cd ~/code/seqr/deploy/kubernetes
    ./seqrctl deploy-and-load {label}   # label can be 'local' or 'gcloud'


The `./seqrctl` script provides subcommands for deploying seqr components, loading reference and example datasets, and
 performing common development and troubleshooting steps. It supports these additional commands:
         
      deploy-and-load  {local,gcloud}                        # End-to-end deployment - deploys all seqr components and loads reference data + an example project
      deploy {postgres,phenotips,mongo,seqr,nginx,matchbox} {local,gcloud}  # Deploy one or more components
      load  {reference-data,example-project}                 #  Load reference or example datasets to initialize seqr
      logs {postgres,phenotips,mongo,seqr,nginx,matchbox}    # show logs for one or more components
      forward {postgres,phenotips,mongo,seqr,nginx,matchbox} # start port-forwarding for service(s) running in the given component container(s), allowing connections via localhost
      connect-to {postgres,phenotips,mongo,seqr,nginx,matchbox}  # starts port-forwarding and shows logs
      shell {postgres,phenotips,mongo,seqr,nginx,matchbox}   # open a bash shell inside one of the component containers
      create-user                                            # create a seqr admin user
      status                                                 # print status of all kubernetes and docker subsystems
      dashboard                                              # open the kubernetes dasbhoard in a browser
      kill {postgres,phenotips,mongo,seqr,nginx,matchbox}    # removes pods and other entities of the give component - the opposite of deploy.
      delete {seqrdb,phenotipsdb,mongodb}                    # clears the given database - deleteing all records
      kill-and-delete-all {local, gcloud}                    # kill and deletes all resources, components and data - reseting the kubernetes environment to as close to a clean slate as possible



Kubernetes Resources
--------------------

- Official Kuberentes User Guide:  https://kubernetes.io/docs/user-guide/
- 15 Kubernetes Features in 15 Minutes: https://www.youtube.com/watch?v=o85VR90RGNQ
- Kubernetes: Up and Running: https://www.safaribooksonline.com/library/view/kubernetes-up-and/9781491935668/
- The Children's Illustrated Guide to Kubernetes: https://deis.com/blog/2016/kubernetes-illustrated-guide/

