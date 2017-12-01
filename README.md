
seqr 
====
[![Build Status](https://travis-ci.org/macarthur-lab/seqr.svg?branch=master)](https://travis-ci.org/macarthur-lab/seqr)

seqr is a web-based analysis tool for rare disease genomics.

This repository contains the code that underlies the [Broad seqr instance](http://seqr.broadinstitute.org), as well as other seqr deployments.

## Overview

seqr consists of the following components or micro-services:
- seqr - the main client-server application - javascript + react.js on the client-side, python + django on the server-side.
- postgres - SQL database used by seqr and phenotips to store metadata and small reference datasets (eg. OMIM, clinvar).
- phenotips - 3rd-party web-based tool for entering structured phenotype information.
- mongo - NoSQL database used to store large variant datasets and reference data. This is being phased out in favor of elasticsearch.
- matchbox - a service that encapsulates communication with the Match Maker Exchange
- nginx - http server used as the main gateway between seqr and the internet.
- elasticsearch - NoSQL database that's replacing mongo as the database storing reference data and variant callsets in seqr.
- kibana - (optional) user-friendly visual interface to elasticsearch.


## Installation

We are now using [Kubernetes](https://kubernetes.io/) for local, dev, and production deployments of seqr. This allows  deployments to work the same way on different operating systems (MacOSX, Linux or Windows) and for both local and cloud-based deployments on Google, AWS, Azure, Alibaba and other clouds.

For detailed installation instructions click here:

#### [Installation Instructions](https://github.com/macarthur-lab/seqr/blob/master/deploy/kubernetes/README.md)


Additionaly, pipelines for pre-processing and loading datasets into seqr are currently located here:

##### [Data pre-processing and loading pipelines](https://github.com/macarthur-lab/hail-elasticsearch-pipelines)
  
**Please Note:** seqr is still under active development, and undergoing refactoring. We suggest you contact us if you want to build on this repo.



