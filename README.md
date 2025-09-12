# seqr

![Unit Tests](https://github.com/broadinstitute/seqr/workflows/Unit%20Tests/badge.svg?branch=master) | ![Local Install Tests](https://github.com/broadinstitute/seqr/workflows/local%20install%20tests/badge.svg?branch=master)

seqr is a web-based tool for rare disease genomics.
This repository contains code that underlies the [Broad seqr instance](http://seqr.broadinstitute.org) and other seqr deployments. To check for any active incidents occurring on the Broad seqr instance, check [here](/INCIDENTS.md)

## Technical Overview

seqr consists of the following components:
- postgres - SQL database used by seqr to store project metadata and user-generated content such as variant notes, etc.
- clickhouse - High-performance SQL database used to store variant data.
- redis - in-memory cache used to speed up request handling.
- seqr - the main client-server application built using react.js, python and django.
- pipeline-runner - server for running hail pipelines to annotate and load new datasets into clickhouse.

## Install

The seqr production instance runs on Google Kubernetes Engine (GKE) and data is loaded using Google Dataproc Spark clusters.

On-prem installs can be created using **[helm](deploy/LOCAL_INSTALL_HELM.md)**

To set up seqr for local development, see instructions **[here](deploy/LOCAL_DEVELOPMENT_INSTALL.md)**  

### Legacy installs

Historically, on-prem installs can use docker-compose to run a version of seqr with an elasticsearch backend.
This backend will be supported through **March 1, 2026**.
If you are setting up a new installation of seqr, do not use this method. However, if you have an existing installation 
you can find documentation for this method here:
 **[Local installs using docker-compose](deploy/LOCAL_INSTALL.md)**

## Updating / Migrating a  seqr Instance	

Instructions for updating an existing seqr instance to the latest version are found 
**[here](https://github.com/broadinstitute/seqr-helm?tab=readme-ov-file#updating-seqr)**

### Legacy installs

Instructions for migrating application data from a docker-compose installation to a helm installation are found
**[here](https://github.com/broadinstitute/seqr-helm?tab=readme-ov-file#migrating-application-data-from-docker-composeyaml)**

Instructions for updating a docker-compose installation to the latest version still using docker-compose are found
**[here](deploy/MIGRATE.md)**

## Contributing to seqr

(Note: section inspired by, and some text copied from, [GATK](https://github.com/broadinstitute/gatk#contribute))

We welcome all contributions to seqr. 
Code should be contributed via GitHub pull requests against the main seqr repository.

If you’d like to report a bug but don’t have time to fix it, you can submit a
[GitHub issue](https://github.com/broadinstitute/seqr/issues/new?assignees=&labels=bug&template=bug_report.md&title=)

For larger features, feel free to discuss your ideas or approach in our 
[discussion forum](https://github.com/broadinstitute/seqr/discussions)

To contribute code:

- Submit a GitHub pull request against the master branch.

- Break your work into small, single-purpose patches whenever possible. 
However, do not break apart features to the point that they are not functional 
(i.e. updates that require changes to both front end and backend code should be submitted as a single change)

- For larger features, add a detailed description to the pull request to explain the changes and your approach

- Make sure that your code passes all our tests and style linting

- Add unit tests for all new python code you've written

We tend to do fairly close readings of pull requests, and you may get a lot of comments.

Thank you for getting involved!
