Feature List
============

This page lists all the different features in xBrowse: a quick description of each, as well as how stable and how complete it is.

- "Stable" refers to how reliable it is - *stable* indicates that it has been thoroughly tested and no bugs remain.
- "Complete" refers to the development status - if we are still working on the feature, and how likely it is to change in the coming months.

I'd be remiss not to include a note that xBrowse aims to be a cohesive platform -
so it's a bit misleading to separate everything into discrete features -
but this is nevertheless a useful abstraction.



## Analysis Modules

### Mendelian Variant Search

The canonical xBrowse search interface - this encompasses a large majority of xBrowse use.
[More info](mendelian-variant-search)

- Stable
- Complete, but subject to continuous minor improvements

### Combine Mendelian Families

Combine results of Mendelian Variant Search across a family group.

- Almost stable
- Incomplete - we have a long queue of features to add to make this more useful

### Cohort Gene Search

Search for genes that contain a burden of interesting variants when compared to a control cohort.

- Unstable - there are some known issues that we need to fix
- Incomplete

### Cohort Variant Search

Search for variants within a cohort

- Stable
- Incomplete - we plan to overhaul this at some point soon

### Exome Coverage Report

View the sequencing coverage for a single gene or across a set of genes.
Aims to answer the question "if there were a variant here, would it have been detected?"

- Stable
- Mostly complete - a few more iterations to make this more useful.

### CNV Report

Analyze CNV calls alongside NGS variant calls.
Current plan is to allow users to upload arbitrary variant calls from exome CNV callers, CNV chip, or whole genome CNV callers.
Generation of CNV calls will not be part of xBrowse, but we will distribute instructions for generating CNVs from exome data.

- Prototype in progress. We have an internal exome CNV pipeline we can run on cooperative data until this is integrated into xBrowse.

### Diagnostic Search

View a list of candidate genes in a *diagnostic mode* - highlight any possible evidence for causal variation.

- Prototype in progress



## Project Management

### Saving Variants

Users can save a variant in a family, and view previously saved variants in a family or across an entire project.

- Mostly stable - functionality is quite simple, but the metadata collected may change
- Mostly complete; you still can't delete previously saved variants

### Analysis Status

Users can track which families are solved and unsolved.
We also want to support tracking *which* analyses have been performed on a family.

- Stable
- "Solved" is complete, but granular analysis tracking is in the planning stage

### Collaborators

Managers can add and remove collaborators on a project.

- Stable
- Mostly complete; just need to add a couple convenience utilities



## Data Input

### Custom Reference Populations

Projects can filter against custom reference populations.

- Stable
- Mostly complete - we still must upload panels manually

### Gene Lists

Upload a list of genes - usually known disease genes - and have those genes highlighted in search results.

- Stable

### Variant Lists

Similar to gene lists, but a list of variants (eg. ClinVar).

- Prototype in progress



## Visualizations

### Gene/Tissue Expression

See how a gene is differentially expressed across tissues from RNA/Seq data (GTeX)

- Stable
- Mostly complete; we just need to update data sources

### Raw Read Visualization

Inspect raw reads for an individual variant, to see if it's real

- Prototype in progress

### Reference Coding Variation

An optimized browser view for summarizing the reference variation in a gene

- Prototype in progress



## Planned Features

### Family Exome QC

Basic QC heuristics from family exome data

### Exome Relatedness Predictions

Predict IBD from exome data - to be used for QC, to verify pedigrees.

### RNA/Seq

Visualize patient RNA/Seq data alongside exome variation.

### Pedigree Visualization

This is by far the most requested feature in xBrowse, but has proven disturbingly elusive.
Anybody care to intern at ATGU and implement this?