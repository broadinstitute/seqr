Loading Data
============

This page describes how data is loaded into xBrowse.
For more background on how data is organized internally, see <a href="data-organization">data organization</a>.
Currently there is no automated upload process - all data must be loaded by hand by the ATGU staff.
It's a simple process, you just have to email us the necessary input files and we run a quick script.
We will add an automatic upload feature at some point - we just haven't had the time yet.

### Step 1: Sample Data

We've adopted the convention of loading all sample and phenotype data into xBrowse before variant data.
This helps us stay organized and enables an important class of QC -
that your genotype data is actually what you are expecting.

Sample data can be sent in a variety of optional tab-delimited text files; these are described below.

#### FAM files

If you are uploading any families into xBrowse (as opposed to cohorts of isolated probands)
you must specify the relationships in a FAM file.
The FAM file format is described in detail on the
[PLINK website](http://pngu.mgh.harvard.edu/~purcell/plink/data.shtml#long).

A quick primer: FAM files have one line per individual with the following fields:

    FAMILY_ID   INDIVIDUAL_ID   MATERNAL_ID PATERNAL_ID GENDER  AFFECTED_STATUS

Some notes that are specific to xBrowse:

- All of the *_ID fields must be "slugs" - a combination of letters, numbers, `_` and `-`.
Periods are not allowed in any of the ID fields.

- `INDIVIDUAL_ID` should be *exactly* the ID in a VCF file, and is case sensitive.

- Any of the final four fields can be set to `.` if unknown

- Only specify `MATERNAL_ID` or `PATERNAL_ID` if there is in fact genotype data on this individual.
If not, leave it as `.`.
This is not ideal, and was poor design on Brett's part when we first built xBrowse.
It means that two siblings are stored the same way as two affected cousins.
We are exploring a fix for this.

- The `GENDER` is coded as `2` -> Female; `1` -> Male; `.` -> Unknown

- The `AFFECTED_STATUS` is coded as `2` -> Affected; `1` -> Unaffected; `.` -> Unknown

### Sample List Files

The FAM files above only make sense if you are actually loading families.
If you are loading cohorts, you can load sample data from a *sample list file* instead,
which is just a FAM file with only the `INDIVIDUAL_ID` column: a text file with a list of IDs, one per line.
Like FAM files, this ID must match the VCF file exactly.

#### Nickname Files

We mention above that INDIVIDUAL_ID must be the exact ID in a VCF file.
Working with these identifiers can get frustrating sometimes;
you can optionally assign a more human readable *nickname* to samples if you prefer.

Nicknames are specified in a *nickname file*, with the following fields:

    INDIVIDUAL_ID   NICKNAME

`INDIVIDUAL_ID` must match the FAM file exactly. `NICKNAME` can have spaces.

#### Pedigree Diagrams

For complex pedigrees, it can be helpful to have a traditional pedigree diagram to cross-reference.
For now, just email us pedigree diagrams if you have them and we can load them manually.

#### Phenotype Files

The FAM file description above only allows you to specify affected status,
yet it can often be helpful to load more detailed phenotype information.
You can load more granular phenotype information in a *phenotype file*, with the following fields:

    INDIVIDUAL_ID   PHENOTYPES

`PHENOTYPES` is a comma separated list of phenotype tags. These must be slugs, but you can define the phenotype.
Note that even though this is a flat key/value representation, it usually represents some type of phenotype heirarchy.
For example, your project might contain a set of Muscular Dystrophy patients.
All of the affected individuals will be tagged with `muscular_dystrophy`,
but a subset could be tagged with `limbgirdle_muscular_dystrophy`, indicating the subtupe of Muscular Dystrophy.
An overlapping set could could be tagged with `has_pain`.

Right now xBrowse does not provide much support for phenotypes, but this is something we are actively working on.
We want people to be able to use xBrowse to search for genes that predict subphenotypes.

### Step 2: Genetic Data

The main input to xBrowse is <a href="www.1000genomes.org/wiki/Analysis/Variant Call Format/vcf-variant-call-format-version-41">VCF files</a>.
VCFs are assumed to be produced by the GATK,
though data from some other variant calling pipelines can sometimes be used, too.

**Note**: We are working on adding an optional BAM file input as well,
which will allow you to view raw read data alongside variant calls, but this isn't finished yet.

VCF files are often too big to email, you can send us VCF files in any way you prefer.
One restriction is that all the exome data for any individual must be in the same VCF file,
so if you split your VCFs by chromosome you might have to rn `vcf-merge` first.
VCF files can be split by individual, though.