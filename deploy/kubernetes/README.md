This README describes how to deploy a local or a cloud-based instance of seqr using [Kubernetes](https://kubernetes.io/).

Overview
--------

seqr consists of the following components or micro-services:
- seqr - the main client-server application - javascript + react.js on the client-side, python + django on the server-side.
- postgres - SQL database used by seqr and phenotips to store metadata and small reference datasets (eg. OMIM, clinvar).
- phenotips - 3rd-party web-based tool for entering structured phenotype information.
- mongo - NoSQL database used to store large variant datasets and reference data. This is being phased out in favor of elasticsearch.
- matchbox - a service that encapsulates communication with the Match Maker Exchange
- nginx - http server used as the main gateway between seqr and the internet.
- elasticsearch - NoSQL database that's replacing mongo as the database storing reference data and variant callsets in seqr.
- kibana - (optional) user-friendly visual interface to elasticsearch.



Prerequisites
-------------

1. Clone this github repo to a subdirectory of your `HOME` directory (for example, `~/code/seqr`):

       cd ~/code
       git clone https://github.com/macarthur-lab/seqr.git
       cd seqr

   NOTE: Putting the code directory underneath your home directory makes it easier to edit code and have the changes instantly appear inside a seqr pod running in a local minikube instance because minikube automatically mounts your home directory into its VM. 

2. Make sure `python2.7` and [pip](https://pip.pypa.io/en/stable/) are installed.
3. Install python dependencies: 
       
       pip install --upgrade -r ./deploy/requirements.txt

NOTE: You can use the pip `--user` flag or use [virtualenv](https://virtualenv.pypa.io/en/stable/) to isolate seqr python dependencies from your system-wide python instance.     



Create Kubernetes Cluster
-------------------------

**Local instance (MacOSX or other operating system)**

1. [Install Minicube](https://kubernetes.io/docs/tasks/tools/install-minikube/)
  
2. [Install kubectl](https://kubernetes.io/docs/tasks/kubectl/install/) 

3. Start a local minikube kubernetes cluster:
    
    ```
    ./deploy/start_minikube.sh
    ```
 

**Cloud-based instance**

These steps have been tested on Google cloud, but should also work on any cloud that supports Kubernetes:

1. Install Docker  ([MacOSX installer](https://getcarina.com/docs/tutorials/docker-install-mac/) ) 

2. [Install kubectl](https://kubernetes.io/docs/tasks/kubectl/install/)

3. Create a Kuberentes cluster using cloud provider-specific instructions (eg. [Google](https://cloud.google.com/kubernetes-engine/docs/quickstart), [AWS](https://kubernetes.io/docs/getting-started-guides/aws/), [Azure](https://kubernetes.io/docs/getting-started-guides/azure/), [alibaba](https://kubernetes.io/docs/getting-started-guides/alibaba-cloud/), [others](https://kubernetes.io/partners/))


Deploy and Manage Seqr
----------------------

To deploy all seqr components to your Kubernetes environment:

    ./servctl deploy-all minikube
   
The `./servctl` script provides subcommands for deploying and interacting with seqr components, and
 performing other common development and troubleshooting operations. 
 
 Run `./servctl -h` to see all available subcommands. The most commonly used ones are:

      deploy-all-and-load  {deployment-target}              # end-to-end deployment - deploys all seqr components and loads reference data + an example project
      deploy {component-name} {deployment-target}           # deploy one or more components
      
      status {deployment-target}                            # print status of all kubernetes and docker subsystems
      set-env {deployment-target}                           # deploy one or more components
      dashboard {deployment-target}                         # open the kubernetes dasbhoard in a browser
      
      shell {component-name} {deployment-target}            # open a bash shell inside one of the component containers
      logs {component-name} {deployment-target}             # show logs for one or more components
      troubleshoot {component-name} {deployment-target}     # print more detailed info that may be useful for discovering why a component is failing during pod initialization
      connect-to {component-name} {deployment-target}       # shows logs, and also sets up a proxy so that the server running inside this component can be accessed from http://localhost:<port> 
      
      copy-to {component-name} {deployment-target} {local-path}           # copy a local file to one of the pods
      copy-from {component-name} {deployment-target} {path} {local-path}  # copy a file from one of the pods to a local directory
      
      delete {component-name} {deployment-target}           # undeploys the component
      
    *** {component-name}  should be one of these:  init-cluster, secrets, nginx, phenotips, postgres, seqr, etc. 
    *** {deployment-target}  should be one of these:  minikube, gcloud-dev, or gcloud-prod 


Adjust Settings
---------------

The seqr installation steps above should produce a working instance with default settings. You will likely also want to configure settings and secrets in the files below. After any changes, you will need to re-deploy those components for the chagnes to take effect:

       `deploy/kubernetes/*-settings.yaml` - these files contain non-secret settings for each type of deployment, and are intended to  be only non-secret settings that vary across different deployments.  

       `deploy/secrets/*/*.*` - these directories contain private or sensitive settings for each seqr component - such as passwords, tockens, and SSL keys. Changes to these files should NOT be committed to github. Instead they are securely handed to kubernetes and injected into relevant components during deployment using Kubernetes secrets-related features.    
    
   
Kubernetes Resources
--------------------

- Official Kuberentes User Guide:  https://kubernetes.io/docs/user-guide/
- 15 Kubernetes Features in 15 Minutes: https://www.youtube.com/watch?v=o85VR90RGNQ
- Kubernetes: Up and Running: https://www.safaribooksonline.com/library/view/kubernetes-up-and/9781491935668/
- The Children's Illustrated Guide to Kubernetes: https://deis.com/blog/2016/kubernetes-illustrated-guide/

