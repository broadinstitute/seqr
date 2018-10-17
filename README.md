
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
- matchbox - a tool for connecting with the Match Maker Exchange.
- nginx - http server used as the main gateway between seqr and the internet.
- pipeline-runner - container for running hail pipelines to annotate and load new datasets.
- redis - in-memory cache used to speed up request handling.
- elasticsearch - NoSQL database used to store variant callsets.
- kibana - dashboard and visual interface for elasticsearch.
- mongo - legacy NoSQL database originally used for variant callsets and still used now to store some reference data and logs.

These components can be deployed on local or cloud-based hardware.
A laptop with 4 CPUs and 16G RAM may be sufficient for small datasets.
The seqr [production instance](http://seqr.broadinstitute.org) currently uses two n1-highmem-4 (4 vCPUs, 26 GB memory) servers on google cloud + separate servers for the elasticsearch database.
The pipeline for loading new datasets uses Spark to parallelize VEP and other annotation steps. This pipeline can run on the same machine that's hosting seqr components, but running on a separate Spark cluster will allow much processing and loading speeds proportional to the number of nodes and CPUs .


## Install

seqr can be installed on a laptop or on-prem server(s) using installation scripts in the deploy/ directory:
  
**[Detailed instructions for local installations](deploy/LOCAL_INSTALL.md)**.  

For cloud-based deployments, there are Docker images and Kubernetes configs: 

**[Detailed instructions for Kubernetes deployments](deploy/KUBERNETES.md)**.  


## Updating / Migrating an older xBrowse Instance

For notes on how to update an older xbrowse instance, see  

[Update/Migration Instructions](https://github.com/macarthur-lab/seqr/blob/master/deploy/MIGRATE.md)


## Data loading pipelines

seqr uses [hail](http://hail.is)-based pipelines to run VEP and add in other reference data before loading them into elasticsearch.
These pipelines can be run locally on a single machine or on-prem spark cluster, or on a cloud-based spark cluster like Google Dataproc.
We are working on integrating these pipelines so that they are launched and managed by seqr.
For now, they must be run manually, as shown in the examples below. 
The code for these pipelines is in the [hail_elasticsearch_pipelines](https://github.com/macarthur-lab/hail-elasticsearch-pipelines)
repo (which is a submodule of the seqr git repo).

Example with seqr deployed to google cloud GKE, and using Google Dataproc to run the pipeline:
```
# these commands should be run locally on your laptop
git clone git@github.com:macarthur-lab/hail-elasticsearch-pipelines.git

cd hail-elasticsearch-pipelines
export IP=56.4.0.3   # IP address of elasticsearch instance running on google cloud on the project-default network so that it's visible to dataproc nodes, but not to the public internet.
export SEQR_PROJECT_GUID=R003_seqr_project3  # guid of existing seqr project
export GS_VCF_PATH=gs://seqr-datasets/GRCh38/my-new-dataset.vcf.gz   # VCF path on cloud storage

# this will create a new dataproc cluster and submit the pipeline to it
python gcloud_dataproc/load_dataset.py --genome-version GRCh38 --host $IP --project-guid SEQR_PROJECT_GUID --sample-type WGS --dataset-type VARIANTS $GS_VCF_PATH --es-block-size 50

# after the pipeline completes successfully, you can link the new elasticsearch index to the seqr project by using the 'Edit Datasets' dialog on the project page.
```

