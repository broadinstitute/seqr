
seqr 
====
[![Build Status](https://travis-ci.org/macarthur-lab/seqr.svg?branch=master)](https://travis-ci.org/macarthur-lab/seqr)

seqr is a web-based analysis tool for rare disease genomics.

This repository contains the code that underlies the [Broad seqr instance](http://seqr.broadinstitute.org), as well as other seqr deployments.

## Overview

seqr consists of the following components or micro-services:
- seqr - the main client-server application - javascript + react.js on the client-side, python + django on the server-side.
- postgres - SQL database used by seqr and phenotips to store project metadata and user-generated content such as variant notes, etc.
- phenotips - 3rd-party web-based tool for entering structured phenotype information.
- mongo - NoSQL database used to store variant callsets and reference data.
- matchbox - a service that encapsulates communication with the Match Maker Exchange.
- nginx - http server used as the main gateway between seqr and the internet.
- elasticsearch - NoSQL database alternative to mongo that currently supports loading large callsets using a Spark-based [hail](http://hail.is) pipeline.
- kibana - (optional) dashboard and visual interface for elasticsearch.


## Installation

[Kubernetes-based Installation Instructions](https://github.com/macarthur-lab/seqr/blob/master/deploy/kubernetes) - The [Kubernetes](https://kubernetes.io/)-based installation allows for fully scripted deployment of all seqr components. It supports local installation on any operating system using a virtualized environment ([minikube](https://github.com/kubernetes/minikube)) as well as cloud deployment on Google, AWS, and other clouds.  

[Manual Installation Instructions](https://github.com/macarthur-lab/seqr/tree/master/deploy/mac_osx) - walks through the steps to install all seqr components on MacOSX.  

[Data pre-processing and loading pipelines](https://github.com/macarthur-lab/hail-elasticsearch-pipelines) - [hail](http://hail.is) pipelines for pre-processing and loading datasets into an elasticsearch datastore.  
  
**Please Note:** seqr is still under active development, and undergoing refactoring. We suggest you contact us if you want to build on this repo.
