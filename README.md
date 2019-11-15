
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


## Updating a local installation from the v01 to the v02 hail/elasticsearch loading pipeline:

For notes on how to update the pipeline, see:

[Pipeline Update Instructions](https://github.com/macarthur-lab/seqr/blob/master/deploy/UPDATE_TO_v02_PIPELINE.md)


## Data loading pipelines

seqr uses a [hail](http://hail.is)-based pipeline to run VEP, add annotations from reference datasets, and write the annotated variant and genotype records to elasticsearch.
This pipeline can be executed locally on a single machine or on-prem spark cluster, or on a cloud-based spark cluster like Google Dataproc. In either case, the pipeline must run on a machine or cluster that has network access to the machine(s) running elasticsearch.
See [hail_elasticsearch_pipelines](https://github.com/macarthur-lab/hail-elasticsearch-pipelines) for additional documentation.

