About xBrowse
================

xBrowse is a platform for studying rare genetic diseases.
It was built to provide genetic researchers and clinical geneticists a collaborative way to search for the causes of genetic disease using exome sequencing data. Here are some of the things that can be done with xBrowse:

- **Inheritance Mode Search**: Filter for potentially causal variants that adhere to a specific Mendelian mode of inheritance. 
- **Custom Inheritance Search**: In cases with complex pedigrees, this search features allows users to specify genotype on an individual basis. 
- **Gene Search**: Restrict search space to a specific subset of genes.
- **Cohort Search**: Intended to search for potential disease genes in cohorts of unrelated individuals that share a rare phenotype.

### How It Works

xBrowse accepts as input a set of variant calls from a whole exome or whole genome sequencing study.
Currently, the only accepted input format is a *VCF file* produced by the *GATK* pipeline.

All VCF data in xBrowse has been passed through a pre-processing pipeline that runs basic quality control metrics and uses Variant Effect Predictor (VEP) for annotation. This annotated file is loaded into a database and available through a web interface for exploring results. 

The different search modes available in xBrowse can be refined based on a number of options: functional annotation, population frequency, variant call quality, and location.

### What sets xBrowse apart:

- **Rapid development**: Genetics moves fast, and we are constantly updating xBrowse with new features and reference data.
- **For researchers**: We’ve really tried to make xBrowse easy to use – we built it exactly as we want to use it.
- **Domain expertise**: Mark Daly and Daniel MacArthur are fantastic researchers, and many of their good ideas and methods are reflected in xBrowse. We hope that their expertise balances out Brett’s naiveté.
- **Reference data**: xBrowse allows you access to a variety of reference databases such as population variation and gene expression data. We hope to add many more as they become available.
- **Open source**: All of the important analysis code is open source and can be run locally. We’re committed to making the open source analysis package as easy to use as possible.

### Who We Are

xBrowse was developed by Brett Thomas, Daniel MacArthur and Mark Daly at the Analytic and Translational Genetics Unit at Massachusetts General Hospital.
