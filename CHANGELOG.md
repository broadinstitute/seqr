# _seqr_ Changes

## dev
* Add db indices for RNAseq outlier models (REQUIRES DB MIGRATION)

## 4/25/22
* Trigger airflow DAG on AnVIL loading request

## 4/19/22
* Add data type to family analysed by (REQUIRES DB MIGRATION)
* Add ClinGen reference data (REQUIRES DB MIGRATION)

## 4/11/22
* Remove pre-built static assets (REQUIRES IMAGE UPDATE)

## 3/25/22
* Update display for translocations

## 3/18/22
* Disallow deleting individuals in matchmaker (REQUIRES DB MIGRATION)
* Add GenCC reference data (REQUIRES DB MIGRATION)
* Update local pipeline to use latest clinvar

## 3/10/22
* Return hom alt SNPs in trans with Deletions as compound hets
* Disable variant download in demo projects (REQUIRES DB MIGRATION)

## 3/2/22
* Update seqr dockerfile to improve immutability and build automation (REQUIRES IMAGE UPDATE)
* Adds NPM asset build to the seqr dockerfile
* Bumps major version of react/ redux

## 2/4/22
* Show RNA-seq expression data (REQUIRES DB MIGRATION)
* Allow deletion of analysed families (REQUIRES DB MIGRATION)
* Allow bulk updating assigned analysts

## 1/27/22
* Separate structural annotation search for gCNV and genome SVs

## 1/26/22
* Improved usage for docker-compose pipeline runner
* Add support for serving the django media root out of a google cloud storage bucket

## 1/21/22
* Support setting explicit order for saved search display (REQUIRES DB MIGRATION)

## 1/7/22
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
