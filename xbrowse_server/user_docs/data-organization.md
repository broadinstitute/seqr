How Data is Organized in xBrowse
================================

### Projects

Projects are the central organizational unit in xBrowse - all research data is assigned to a project. 
A variety of project settings are available for configuring how data is analyzed in a particular project. 

The specification for what exactly should constitute a project is purposely vague. 
In some cases, it will make sense to load all samples from a collaboration into the same project.
In others, it may make sense to isolate data in separate projects. 

Also note that user permissions are organized around projects - 
the list you see on the homepage is the list of projects that have been assigned to your account. 

A project can have any number (including zero) of Individuals, Families, and Cohorts. 

### Sample Data

xBrowse adopts the following nomenclature to describe samples: 

- An **Individual** is a single human being (as xBrowse is only for human data)

- A **Variant Dataset** is specifically set of variant calls from next generation sequencing data, usually loaded from a VCF file. Can be whole exome or whole genome data. 

- A **Sample** is data from one individual in one variant dataset. 

So, suppose you have a project with whole exome and whole genome data for a single parent/proband trio. 
It will contain 3 individuals, 2 VCF datasets, and 9 samples. 

### Families

A family is a collection of one or more related individuals. 
You may add individuals to xBrowse that do not have sequencing data - 
so a family can also contain relatives that are not under study but are still relevant for Mendelian analysis. 

It is important to make sure that individuals are explicitly assigned to a family. 
For example, you can't run *Mendelian Variant Search* on an individual - but you can on a family with one individual. 

First time users may find this confusing and arbitrary, but it's important for keeping data organized under the hood. 

An individual cannot be assigned to multiple families. 

### Family Groups

One of the powerful features in xBrowse is the ability to intelligently combine data from multiple Mendelian families. 
In order to run any of the multiple-family analyses, you must explicitly create a family group. 

A family group can (and usually does) contain families with a variety of pedigree structures. 

### Cohorts

A cohort in xBrowse is an arbitrary set of individuals that you want to analyze together. 

Note that we used to define a cohort specifically as a set of unrelated probands - *this is no longer the case*. 
A cohort is any set of individuals that you need to group together for any purpose. 

Cohort functionality is very preliminary at the moment. 
There are assorted analyses that we want to add to xBrowse require grouping individuals - 
visualizing samples together, comparing different populations, etc. 

Under the hood, these features don't always align with the Family/Family Group paradigm, 
thus we've created this "Cohort" entity. 

An indiviudal can be included in multiple cohorts. 