# _seqr_ Changes

## dev

## 1/7/21
* Update variant layout
* Project page performance optimization

## 12/24/21
* Show RNA-seq outlier data (REQUIRES DB MIGRATION)

## 12/07/21
* Show delay warning on AnVIL loading requests

## 11/23/21
* Update the seqr Dockerfile base image from debian:stretch to python:3.7-slim-bullseye
* Consolidation and cleanup of various RUN tasks in the seqr Dockerfile

## 11/17/21
* Update pathogenicity search to override frequency filters
* Add ACMG classifier to variants (REQUIRES DB MIGRATION)

## 11/10/21
* Update in-silico score filtering behavior and add splice AI override

## 10/25/21
* Add search filtering by in-silico score

## 10/21/21
* Support updated WES SV loading pipeline format

## 9/30/21
* Allow project-specific HGMD access (REQUIRES DB MIGRATION)
* Demo project available to all users (REQUIRES DB MIGRATION)
* Update pedigree label display (requires manual cleanup for saved pedigree datasets)
* Support application downtime/ warning messages (REQUIRES DB MIGRATION)

## 9/17/21
* Change family note fields into lists of notes (REQUIRES DB MIGRATION)
* Add Panel App gene list integration (REQUIRES DB MIGRATION)

## 9/10/21
* Use google storage API instead of gsutil for IGV 

## 9/3/21
* Add last updated information for family analysis_status (REQUIRES DB MIGRATION)

## 8/25/21
* Better validation for MME match results
* Send notification when adding dataset

## 8/20/21
* Support loading/ searching data using ES aliases
* Added changelog
