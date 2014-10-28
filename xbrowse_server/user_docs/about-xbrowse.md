About xBrowse
================

xBrowse is a platform for studying rare genetic diseases.
It was built to provide genetic researchers and clinical geneticists a way to search for the causes of genetic disease
using exome sequencing data. Here are some of the things you can do with xBrowse:

- **Pedigree Search**: If you have a family with a Mendelian disease, you can use xBrowse to help identify the causal mutation.
- **Cohort Search**: If you have a cohort of unrelated individuals that share a rare phenotype,
you can use xBrowse to search for potential disease genes.

### How It Works

xBrowse accepts as input a set of variant calls from an exome sequencing study.
Currently, the only accepted input format is *VCF file* produced by the *GATK*.

The first step to loading data into xBrowse is processing the VCF file through a pre-processing pipeline.
This pipeline runs some basic quality control checks on the VCF file and annotates it with the Variant Effect Predictor (VEP).
The annotated VCF file is then parsed and loaded into a database.

After loading has completed, a web interface is available for exploring results.
There are two main search modes, Family Variant Search and Cohort Gene Search (described above).
Each exposes a number of options for searching variants, including functional annotation, population frequency, and variant call quality.

### Goals

There are a bunch of tools like this, so here are a few things that we think sets xBrowse apart:

- **Rapid development**: genetics moves fast, and we are constantly updating xBrowse with new features and reference data.
- **For researchers**: we’ve really tried to make xBrowse as easy as possible – we built it exactly as we want to use it.
- **Domain expertise**: Mark Daly and Daniel MacArthur are really fantastic researchers, and many of their good ideas and methods are contained in xBrowse. We hope that their expertise balances out Brett’s naiveté.
- **Reference data**: xBrowse allows you to reference a variety of reference databases, such as population variation, gene expression data. We hope to add many more as they become available.
- **Open source**: All of the important analysis code is open source and can be run locally. We’re committed to making the open source analysis package as easy to use as possible.

### Who We Are

xBrowse was developed at the Analytic and Translational Genetics Unit at Massachusetts General Hospital.
It was developed by Brett Thomas, Daniel MacArthur and Mark Daly.