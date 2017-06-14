
seqr 
====
[![Build Status](https://travis-ci.org/macarthur-lab/seqr.svg?branch=master)](https://travis-ci.org/macarthur-lab/seqr)

seqr is a software package for working with next generation sequencing data,
specifically in the context of studying rare genetic diseases.

This package contains the analysis code that powers the [seqr website](http://seqr.broadinstitute.org).

## Local Installation

**Please Note:** This package is in active development, and the API is extremely unstable. We suggest you contact us if you want to build on this repo.

To install seqr on your laptop, server, or private cloud environment, we recommend using the Kubernetes-based deployment: 

* Kubernetes-based deployment: [deploy/kubernetes/README.md](deploy/kubernetes/README.md)

A set of legacy installation scripts is also available here:

* seqr local install: [deploy/mac_osx/README.md](deploy/mac_osx/README.md)  


## Development Plans

Current refactoring plans include:
* refactor metadata schema to support multiple samples per individual (for example, when individuals that have both WGS and exome variant calls). 
* refactor the UI to use React.js
* move from mongodb to a different freely-available database backend
