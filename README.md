
seqr
====
[![Build Status](https://travis-ci.org/broadinstitute/seqr.svg?branch=master)](https://travis-ci.org/broadinstitute/seqr)

seqr is a web-based tool for rare disease genomics.
This repository contains code that underlies the [Broad seqr instance](http://seqr.broadinstitute.org) and other seqr deployments. To check for any active incidents occuring on the Broad seqr instance, check [here](/INCIDENTS.md)

## Technical Overview

seqr consists of the following components:
- postgres - SQL database used by seqr to store project metadata and user-generated content such as variant notes, etc.
- elasticsearch - NoSQL database used to store variant callsets.
- redis - in-memory cache used to speed up request handling.
- seqr - the main client-server application built using react.js, python and django.
- pipeline-runner - optional container for running hail pipelines to annotate and load new datasets into elasticsearch. If seqr is hosted on google cloud (GKE or GCE), Dataproc spark clusters can be used instead.
- kibana - optional dashboard and visual interface for elasticsearch.

## Install

The seqr production instance runs on Google Kubernetes Engine (GKE) and data is loaded using Google Dataproc Spark clusters. 

On-prem installs can be created using docker-compose:
**[Local installs using docker-compose](deploy/LOCAL_INSTALL.md)**  


## Updating / Migrating an older seqr Instance	

For notes on how to update an older instance, see  	

[Update/Migration Instructions](deploy/MIGRATE.md)
