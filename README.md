
seqr
====
[![Build Status](https://travis-ci.org/macarthur-lab/seqr.svg?branch=master)](https://travis-ci.org/macarthur-lab/seqr)

seqr is a web-based analysis tool for rare disease genomics.

This repository contains code that underlies the [Broad seqr instance](http://seqr.broadinstitute.org) and other seqr deployments.

## Technical Overview

seqr consists of the following components:
- seqr - the main client-server application. It consists of javascript + react.js on the client-side, python + django on the server-side.
- postgres - SQL database used by seqr and phenotips to store project metadata and user-generated content such as variant notes, etc.
- phenotips - 3rd-party web-based form for entering structured phenotype data.
- matchbox - a service that encapsulates communication with the Match Maker Exchange.
- nginx - http server used as the main gateway between seqr and the internet.
- pipeline-runner - container for running hail pipelines to annotate and load new datasets.
- redis - in-memory cache used to speed up request handling.
- elasticsearch - NoSQL database used to store variant callsets.
- kibana - dashboard and visual interface for elasticsearch.
- mongo - legacy NoSQL database originally used for variant callsets and still used now to store some reference data and logs.

These components can be deployed on local or cloud-based hardware.
A laptop with 4 CPUs and 16G RAM may be sufficient for looking at small datasets.
The seqr production instance (seqr.broadinstitute.org) currently uses two n1-highmem-4 (4 vCPUs, 26 GB memory) servers on google cloud + separate instances for the elasticsearch database.
The pipeline for loading new datasets uses Spark to parallelelize VEP and other annotation steps. This pipeline can run on the same machine 
that's hosting other seqr components, but a separate Spark cluster will make the loading process faster.


## Install

Whether installing seqr on a laptop, on-prem, or cloud VMs, we use Docker images and Kubernetes to automate the deployment steps and isolate them from the operating system.
Users that are very familiar with the components that make up seqr may want to install them directly on host systems. This provides maximum control, but requires more work up front. 
If you decide to go this route, the [Dockerfiles](https://github.com/macarthur-lab/seqr/tree/master/deploy/docker) can be useful as a list of steps for installing each component.  
In most cases, we recommend the docker/kubernetes approach because:  1) it automates deployment as much as possible 2) as seqr evolves, this makes it easier to roll out new 
components or move around existing components if they outgrow existing hardware.   
The instructions below cover local deployments using Minikube, but are also relevant for cloud-based deployments.

#### Step 1: Install Kubernetes

Local and on-prem installations can use [MiniKube](https://kubernetes.io/docs/setup/minikube/) to create a self-contained kubernetes cluster on a single machine. 
For deploying to the cloud, we use Google Cloud Container Engine (GKE), but many other cloud providers also have native kubernetes support.
A list of other options can be found at: https://kubernetes.io/docs/setup/pick-right-solution/

Prereqs: `python2.7`, `sudo` root access. MacOS also requires [homebrew](http://brew.sh/) package manager. 

Run the following command to install `gcc`, `java1.8`, `minikube`, `kubectl` and dependencies (using `brew`, `yum` or `apt-get`):

###### MacOS
```
SCRIPT=step1.macos.install_dependencies.sh && curl -L 'http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT' -o $SCRIPT && chmod 777 $SCRIPT && source $SCRIPT
```

###### CentOS7 / RedHat server

```
SCRIPT=step1.linux-centos7.install_dependencies.sh && curl -L 'http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT' -o $SCRIPT && chmod 777 $SCRIPT && source $SCRIPT
```

###### Ubuntu 

```
SCRIPT=step1.linux-ubuntu18.install_dependencies.sh && curl -L 'http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT' -o $SCRIPT && chmod 777 $SCRIPT && source $SCRIPT
```

#### Step 2: Install and start elasticsearch

Run this script to start an elasticsearch instance in the current directory: 
```
SCRIPT=step2.install_and_start_elasticsearch.sh && curl -L 'http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT' -o $SCRIPT && chmod 777 $SCRIPT && source $SCRIPT
```

#### Step 3: Download seqr deployment scripts

In a new terminal, run this script to download seqr deployment scripts:
```
SCRIPT=step3.download_deployment_scripts.sh && curl -L 'http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT' -o $SCRIPT && chmod 777 $SCRIPT && source $SCRIPT
```
  
Optionally edit deployment settings before proceeding to step 4:

* *deploy/kubernetes/minikube-settings.yaml* - contains settings like $MINIKUBE_DISK_SIZE.
* *deploy/secrets/shared/** - directories that contain keys, passwords and other sensitive info that shouldn't be shared publicly. You may at some point want to edit:
  * *gcloud/service-account-key.json* - allows gcloud and kubectl to access google cloud resources in your project from within pods. We provide a placeholder key which can access public resources.
  * *nginx/tls.cert* and *nginx/tls.key* - ssh keys that allow https access and avoid web browser "insecure website" warnings. https connections are critical for encrypting seqr logins, so you will want to order your own keys before making your seqr instance visible over the internet.
  * *seqr/postmark_server_token* - seqr uses this to send outgoing emails via postmark.com mail service
  * *seqr/omim_key* - api key for downloading the latest omim files. We provide a placeholder key, but you'll want to use your own.
  * *matchbox/nodes.json* - contains the list of all nodes that matchbox can connect to on the MME network, along with the authentication token for each node.


#### Step 4: Install seqr on minikube

```
SCRIPT=step4.install_seqr_on_minikube.sh && curl -L 'http://raw.githubusercontent.com/macarthur-lab/seqr/master/deploy/$SCRIPT' -o $SCRIPT && chmod 777 $SCRIPT && source $SCRIPT
```

This may run for several hours to deploy all components and load reference data.

Once it's done with the deployment steps, you can create a super-user account by running:
 

```
source ./activate_virtualenv.sh
./servctl create-user minikube 
```

and open seqr by opening your browser to:

```
open http://$(minikube ip):30003   # here, port 30003 is based on the value of $SEQR_SERVICE_NODE_PORT 
```

## Update / Migrate an older xBrowse Instance

[Update/Migration Instructions](https://github.com/macarthur-lab/seqr/blob/master/deploy/MIGRATE.md)


## Deploy and manage seqr components


The `./servctl` wrapper script provides sub-commands for deploying and interacting with seqr components running on kubernetes.

Run `./servctl -h` to see all available subcommands. The most commonly used ones are:

```
  ./servctl

      deploy-all  {deployment-target}                       # end-to-end deployment - deploys all seqr components
      deploy {component-name} {deployment-target}           # deploy some specific component(s)
          --restore-seqr-db-from-backup  <seqr_db_backup_file.sql.gz>   # deploying seqr with this option will also load the given seqrdb backup into postgres
          --restore-phenotips-db-from-backup  <xwiki_db_backup_file.sql.gz>   # deploying seqr with this option will also load the given phenotips xwikidb backup into postgres
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

      create-user {deployment-target}                       # create seqr superuser
      update-reference-data {deployment-target}             # update gene-level reference data in seqr
      load-example-project {deployment-target}              # run commands in seqr and pipeline-runner to load an example project


  *** {deployment-target} is one of:  minikube, gcloud-dev, or gcloud-prod
  *** {component-name} is one of: init-cluster, settings, secrets, nginx, postgres, phenotips, seqr,
                                  redis, pipeline-runner, matchbox, cockpit, kibana,
                                  external-mongo-connector, external-elasticsearch-connector,
                                  mongo, elasticsearch,
                                  es-client, es-master, es-data, es-kibana
```


## Data loading pipelines

seqr uses [hail](http://hail.is)-based pipelines to run VEP and add in other reference data before loading them into elasticsearch.
These pipelines can be run locally on a single machine or on-prem spark cluster, or on a cloud-based spark cluster like Google Dataproc.
We are working on integrating these pipelines so that they are launched and managed by seqr.
For now, they must be run manually, as shown in the examples below. The code for these pipelines is in [Data annotation and loading pipelines](https://github.com/macarthur-lab/hail-elasticsearch-pipelines)
and is automatically installed in the `pipeline-runner` component which is deployed as part of standard seqr deployment.

Example using minikube:
```
# after you've deployed seqr to minikube, open a shell within the pipeline-runner pod
./servctl shell pipeline-runner minikube

export SEQR_PROJECT_GUID=R003_seqr_project3  # guid of existing seqr project
export VCF_PATH=/data/my-exome-dataset.vcf.gz   # local or google cloud bucket VCF path

/hail-elasticsearch-pipelines/run_hail_locally.sh \
        --driver-memory 5G \
        --executor-memory 5G \
        hail_scripts/v01/load_dataset_to_es.py \
            --genome-version 37 \
            --project-guid $SEQR_PROJECT_GUID \
            --sample-type WES \
            --dataset-type VARIANTS \
            --exclude-hgmd \
            --vep-block-size 10 \
            --es-block-size 10 \
            --num-shards 1 \
            --max-samples-per-index 99 \
            $VCF_PATH

# after the pipeline completes successfully, you can link the new elasticsearch index to the seqr project by using the 'Edit Datasets' dialog on the project page.
```

Example with seqr deployed to google cloud GKE, and using Google Dataproc to run the pipeline:
```
# these commands should be run locally on your laptop
git clone git@github.com:macarthur-lab/hail-elasticsearch-pipelines.git

cd hail-elasticsearch-pipelines
export IP=56.4.0.3   # IP address of elasticsearch instance running on google cloud on the project-default network so that it's visible to dataproc nodes, but not to the public internet.
export SEQR_PROJECT_GUID=R003_seqr_project3  # guid of existing seqr project
export GS_VCF_PATH=gs://seqr-datasets/GRCh38/my-new-dataset.vcf.gz   # VCF path on cloud storage

# this will create a new dataproc cluster and submit the pipeline to it
python gcloud_dataproc/load_GRCh38_dataset.py --host $IP --project-guid SEQR_PROJECT_GUID --sample-type WGS --dataset-type VARIANTS $GS_VCF_PATH --es-block-size 50

# after the pipeline completes successfully, you can link the new elasticsearch index to the seqr project by using the 'Edit Datasets' dialog on the project page.
```


## Kubernetes Resources


- Official Kuberentes User Guide:  https://kubernetes.io/docs/user-guide/
- 15 Kubernetes Features in 15 Minutes: https://www.youtube.com/watch?v=o85VR90RGNQ
- Kubernetes: Up and Running: https://www.safaribooksonline.com/library/view/kubernetes-up-and/9781491935668/
- The Children's Illustrated Guide to Kubernetes: https://deis.com/blog/2016/kubernetes-illustrated-guide/
