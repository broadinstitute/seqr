Loading xBrowse Projects
========================

This document describes how to prepare data to be loaded into xBrowse.

**Last edited: 9/14/2014**: This is a work in progress, and we'll probably have to iterate quite a bit to find the best project schema.

## Project Directory 

All data for a project in xBrowse should be contained in a single directory. 
The directory should the same name as the project ID, eg. `macarthur_nmd_1`.  

### project.yaml 

This is a YAML file that describes the project. 
An example project.yaml is included at the bottom. 
All of the data in a project is included in this file, 
either as plain text or as a file path. 

This file contains a bunch of file paths. 
These are *relative* paths to files *within* this directory. 

### external_files.tsv 

Of course, you'll often want to have multiple projects from the same VCF file. 
In this case, the VCF file should *not* be included in this directory. 

Any shared files should be listed in this `external_files.tsv`. 
It is a TSV with two columns. The first is the *file ID* - this is just an identifier string that is used throughout the project. 
The second is the *absolute path* to the file on this filesystem. 
(Again, it should *not* be within the project directory.)

### VCF file 

A project can have any number of gzipped VCF files. 
One sample can only be in one VCF file (so if VCF files are split by chromosome, combine them first.) 
Make sure that every Cohort and Family is only in one VCF file. 

### sample ID list 

This is just a text file listing all the samples in this project. 
Note that a sample can be in the project even if it's not in a VCF file, for example if it hasn't been sequenced yet. 

Finally, a sample ID must only contain letters, numbers, `-` or `_`. 
This is annoying, since many samples sometimes have `.` in them - you must fix this before loading them into xBrowse. 
There are two scripts to assist with this, `scripts/prepare_vcf.py` and `scripts/prepare_ped.py`. 

## Example project.yaml

	--- 

	project_id: 'myproject'

	project_name: 'My Project'

	sample_id_list: 'all_samples.txt'

	ped_files:
	  - 'ped1.ped'
	  - 'ped2.ped'

	vcf_files: 
	  - 'vcf1.vcf.gz'
	  - 'vcf2_file_id' 

	cohorts: 
	  - 
	  	cohort_id: 'cohort1'
	  	cohort_name: 'Cohort 1'
	  	samples: 'cohort1_samples.txt'

## Example external_files.tsv

    vcf2_file_id    /path/to/vcf2.vcf.gz
