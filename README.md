
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


## Install

seqr can be installed on a laptop or on-prem server(s) using installation scripts in the deploy/ directory:
  
**[Detailed instructions for local installations](deploy/LOCAL_INSTALL.md)**  

For cloud-based deployments, there are Docker images and Kubernetes configs: 

**[Detailed instructions for Kubernetes deployments](deploy/KUBERNETES.md)**  


## Updating / Migrating an older xBrowse Instance

For notes on how to update an older xbrowse instance, see  

[Update/Migration Instructions](https://github.com/macarthur-lab/seqr/blob/master/deploy/MIGRATE.md)


## Data loading pipelines

seqr uses [hail](http://hail.is)-based pipelines to run VEP and add in other reference data before loading them into elasticsearch.
These pipelines can be run locally on a single machine or on-prem spark cluster, or on a cloud-based spark cluster like Google Dataproc.
We are working on integrating these pipelines so that they are launched and managed by seqr.
For now, they must be run manually, as shown in the example below. 
See [hail_elasticsearch_pipelines](https://github.com/macarthur-lab/hail-elasticsearch-pipelines)
for additional documentation.

Example with seqr deployed to google cloud GKE, and using Google Dataproc to run the pipeline:
```
# these commands should be run locally on your laptop
git clone git@github.com:macarthur-lab/hail-elasticsearch-pipelines.git

cd hail-elasticsearch-pipelines
HOST=seqr-vm   # IP address or hostname of elasticsearch instance running on google cloud
SEQR_PROJECT_GUID=R003_seqr_project3  # guid of existing seqr project
SAMPLE_TYPE=WGS   # can be WGS or WES
DATASET_TYPE=VARIANTS   # can be "VARIANTS" if the VCF contains GATK or other small variant calls, or "SV" if it contains Manta CNV calls
INPUT_VCF=gs://seqr-datasets/GRCh38/my-new-dataset.vcf.gz  

# this will create a new dataproc cluster and submit the pipeline to it
./gcloud_dataproc/load_dataset.py --genome-version 38 --host ${HOST} --project-guid ${SEQR_PROJECT_GUID} --sample-type ${SAMPLE_TYPE} --dataset-type ${DATASET_TYPE} --es-block-size 50 ${INPUT_VCF}

# after the pipeline completes successfully, you can link the new elasticsearch index to the seqr project by using the 'Edit Datasets' dialog on the project page.
```

