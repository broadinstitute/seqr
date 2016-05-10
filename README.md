
seqr
====

seqr is a software package for working with next generation sequencing data,
specifically in the context of studying rare genetic diseases.

This package contains the analysis code that powers the [seqr website](http://seqr.broadinstitute.org), but 
we welcome anyone wishing to set up their own private instance of seqr.

**Please Note:** This package is in active development, and the API is extremely unstable. We suggest you contact us if you want to build on this repo.

## Installation Instructions

* seqr local install: [deploy/mac_osx/README.md](deploy/mac_osx/README.md)  
* phenotips install instructions: [deploy/mac_osx/PHENOTIPS_INSTALL.md](deploy/mac_osx/PHENOTIPS_INSTALL.md) enable  [PhenoTips](https://github.com/phenotips/phenotips) to be used to enter HPO-based phenotypes from within seqr.

## Development Plans

Current big-picture refactoring plans include:
* refactor meta-data schema to better support multiple samples per individual (eg. for individuals that have both WGS and whole exome variant calls). 
* refactor the UI to use React.js
* move from mongodb to a different backend that's better-optimized for our requirements (currently investigating open-source Apache tools like Solr, as well as managed cloud databases)
