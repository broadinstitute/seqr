# _seqr_ Changes

## dev

## 11/21/24
* Migrate "Submit to Clinvar" to generic report flag for Variant Notes (REQUIRES DB MIGRATION)

## 10/28/24
* Update RNA Tissue Type choices (REQUIRES DB MIGRATION)

## 9/19/24
* Update Biosample choices (REQUIRES DB MIGRATION)
* Add support for Azure OAuth

## 8/14/24
* Remove ONT support (REQUIRES DB MIGRATION)
* Add "Validated Name" functional tag (REQUIRES DB MIGRATION)

## 8/9/24
* Update directory structure for search backend

## 8/2/24
* Adds index_file_path to IGV Sample model (REQUIRES DB MIGRATION)

## 7/24/24
* Split RNA Sample models (REQUIRES DB MIGRATION)

## 7/8/24
* Add VLM contact for Projects (REQUIRES DB MIGRATION)

## 6/11/24
* Add "Partial Phenotype Contribution" functional tag (REQUIRES DB MIGRATION)

## 5/24/24
* Adds external_data to Family model (REQUIRES DB MIGRATION)
* Adds post_discovery_mondo_id to Family model (REQUIRES DB MIGRATION)
* Adds guid and created fields to PhenotypePrioritization model (REQUIRES DB MIGRATION)
* Enable "Reports" tab by default for local installations

## 5/8/24
* Adds dynamic analysis groups (REQUIRES DB MIGRATION)

## 4/4/24
* Add ability to import project metadata from gregor metadata
  * Only enabled for a project if tag is first created via 
    ```
    ./manage.py add_project_tag --name="GREGoR Finding" --order=0.5 --color=#c25fc4 --project=<project>
    ```
* Support FRASER2 data (REQUIRES DB MIGRATION)
* Add solve_status to Individual model (REQUIRES DB MIGRATION)
* Update data deployment for hail backend to disk snapshots

## 3/13/24
* Add "Probably Solved" analysis status (REQUIRES DB MIGRATION)

## 3/1/24
* Add subscribable project notifications (REQUIRES DB MIGRATION)

## 1/8/24
* Support OMIM entries with no associated gene and remove phenotypic_series_number (REQUIRES DB MIGRATION)

## 11/21/23
* Support AIP upload
  * To add the required tag type, run `./manage.py loaddata new_variant_tag_types`

## 11/13/23
* Add Partial Solve analysis status in Family model (REQUIRES DB MIGRATION)

## 10/19/23
* Migrate Family post_discovery_omim_number to integer array (REQUIRES DB MIGRATION)
* Add GeneShet model to the reference DB (REQUIRES DB MIGRATION)

## 10/6/23
* Require tissue_type in Sample model (REQUIRES DB MIGRATION)

## 9/22/23
* Update VARIANTS dataset_type in Sample model (REQUIRES DB MIGRATION)

## 8/22/23
* Add db indices to optimize RNA data queries (REQUIRES DB MIGRATION)

## 7/11/23
* Add internal UI to trigger airflow data loading
* Add RnaSeqSpliceOutlier display

## 6/23/23
* Add a 'rank' field to the RnaSeqSpliceOutlier model (REQUIRES DB MIGRATION)
* Remove hail python dependency

## 6/2/23
* Update Clinvar filtering and display

* Add support for Gencode v39
  * To add new data, run the `update_gencode_latest`

## 4/26/23
* Add RnaSeqSpliceOutlier model (REQUIRES DB MIGRATION)
* Add db index to improve Rna Sample Metadata performance (REQUIRES DB MIGRATION)

## 2/24/23
* Updated Gregor sample manifest (REQUIRES DB MIGRATION)
* Bumps python to 3.9

## 2/15/23
* Support sharded VCFs in AnVIL loading

## 1/11/23
* Require PHI disclaimer when uploading AnVIL pedigree

## 11/9/22
* Add PhenotypePrioritization model (REQUIRES DB MIGRATION)

* Add Refseq and MANE transcript info (REQUIRES DB MIGRATION)
  * To add new data, run the `update_gencode_transcripts` and `update_refseq` commands

## 10/13/22
* Link MME submissions to saved variants (REQUIRES DB MIGRATION)

## 9/28/22
* Add Gregor fields to sample manifest (REQUIRES DB MIGRATION)
* Deprecate auto-granting project access for analysts (removes ANALYST_PROJECT_CATEGORY env variable)
* Add support for adding user groups for project access

## 9/6/22
* Disable mixed authorization for local and AnVIL permissions (REQUIRES DB MIGRATION)

## 8/23/22
* Add consent code for projects (REQUIRES DB MIGRATION)

## 7/19/22
* Add "Incomplete Penetrance" functional tag type (REQUIRES DB MIGRATION)

## 7/12/22
* Add MITO dataset type (REQUIRES DB MIGRATION)

## 6/23/22
* Migrate RGP case note formatting (REQUIRES DB MIGRATION)

## 5/2/22
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
