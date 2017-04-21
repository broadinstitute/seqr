
seqr
====

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

Current big-picture refactoring plans include:
* refactor meta-data schema to better support multiple samples per individual (eg. for individuals that have both WGS and whole exome variant calls). 
* refactor the UI to use React.js
* move from mongodb to a different backend that's better-optimized for our requirements (currently investigating open-source Apache tools like Solr, as well as managed cloud databases)
