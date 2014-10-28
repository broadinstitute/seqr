Loading xBrowse Projects
========================

This document describes how to prepare data to be loaded into xBrowse.
It is for *developers* that want to load into xBrowse on the command line.
Clinical users should reference the [user documentation](https://atgu.mgh.harvard.edu/xbrowse/docs/loading-data) instead.

**Last edited: 10/28/2014**: This is a work in progress, and we'll probably have to iterate quite a bit to find the best project schema.
If anything is confusing, let us know and we'll clarify here.

## Project Directory 

All data for a project in xBrowse should be contained in a single directory. 
The directory should the same name as the project ID, eg. `macarthur_nmd_1`.

## Files

This directory can contain the following files.
Note that not all files are required.
If you just want to load a project quickly, you just need `background.md`, `project.yaml`, a VCF file and a PED file.

#### background.md

This is some background on the project, for *internal* use.
It won't be displayed in the UI anywhere.

Please make sure to include some background on why we are loading data, for which collaborators, etc.
I know it can be a pain when you just want to see results, but we need this to stay organized.
Feel free to paste emails in here too.

#### project.yaml

This is a YAML file that describes the project. 
An example project.yaml is included at the bottom. 
All of the data in a project is included in this file, 
either as plain text or as a file path. 

This file contains a bunch of file paths. 
These are *relative* paths to files *within* this directory. 

#### external_files.tsv

Of course, you'll often want to have multiple projects from the same VCF file. 
In this case, the VCF file should *not* be included in this directory. 

Any shared files should be listed in this `external_files.tsv`. 
It is a TSV with two columns. The first is the *file ID* - this is just an identifier string that is used throughout the project. 
The second is the *absolute path* to the file on this filesystem. 
(Again, it should *not* be within the project directory.)

#### sample ID list

This is just a text file listing all the samples in this project.
Note that a sample can be in the project even if it's not in a VCF file, for example if it hasn't been sequenced yet.

This file is optional; the list of sample IDs will default to all the samples in the VCF files.

Finally, a sample ID must only contain letters, numbers, `-` or `_`.
This is annoying, since many samples sometimes have `.` in them - you must fix this before loading them into xBrowse.
There are two scripts to assist with this, `scripts/prepare_vcf.py` and `scripts/prepare_ped.py`.

#### VCF files

A project can have any number of gzipped VCF files. 
One sample can only be in one VCF file (so if VCF files are split by chromosome, combine them first.) 
Make sure that every Cohort and Family is only in one VCF file.

#### PED files

Pedigree information can be provided by one or more [PED](http://pngu.mgh.harvard.edu/~purcell/plink/data.shtml#ped) files.
We've run across multiple dialects of PED file. This is just a TSV file with the following columns:

    family_id
    individual_id
    paternal_id  (0 or '.' is unknown)
    maternal_id  (0 or '.' is unknown)
    gender  (2=female; 1=male; 0 or '.'=unknown)
    affected_status  (2=affected; 1=unaffected; 0 or '.'=unknown)

In xBrowse, we use *sample ID* and *individual ID* interchangeably.
The IDs in your PED file must match the IDs in the VCF file.
Note that this was not always the case; we added this constraint recently to simplify things.

#### Nickname files

Often the sample IDs in a VCF file are complex and confusing, and you want to use another ID that is more familiar.
You can assign each sample a "nickname", via a TSV file with two columns:

    sample_id  (same as the VCF file)
    nickname  (any string you want. can contain whitespace, though we don't recommend it!)

## Example files

### Minimal configuration

The following is a minimal configuration. The project directory will look like:

    ./
      - project.yaml
      - background.md
      - vcf1.vcf.gz
      - ped1.ped

And `project.yaml` will have:

	---

	project_id: 'myproject'

	ped_files:
	  - 'ped1.ped'

	vcf_files:
	  - 'vcf1.vcf.gz'

### Extensive configuration

Here is a more extensive configuration with all the bells and whistles.

The `project.yaml` is:

	--- 

	project_id: 'myproject'

	project_name: 'My Project'

	sample_id_list: 'all_samples.txt'

	ped_files:
	  - 'sample_data/ped1.ped'
	  - 'sample_data/ped2.ped'

	vcf_files: 
	  - 'vcf1.vcf.gz'
	  - 'vcf2_file_id' 

	nicknames: 'samples/nicknames.tsv'

	cohorts: 
	  - 
	  	cohort_id: 'cohort1'
	  	cohort_name: 'Cohort 1'
	  	samples: 'cohorts/cohort1_samples.txt'
	  -
	  	cohort_id: 'cohort2'
	  	cohort_name: 'Cohort 2'
	  	samples: 'cohorts/cohort2_samples.txt'

And the corresponding directory structure:

    ./
      - project.yaml
      - background.md
      - external_files.tsv
      - vcf1.vcf.gz
      - all_samples.txt
      - sample_data/
        - ped1.ped
        - ped2.ped
        - nicknames.tsv
      - cohorts/
        - cohort1_samples.txt
        - cohort2_samples.txt

`external_files.tsv` then contains:

    vcf2_file_id    /path/to/vcf2.vcf.gz
