Combine Mendelian Families
==========================

*Combine Mendelian Families* is an interface for searching across a set of families.
It allows you to run *Mendelian Variant Search* with the same parameters on a set of families -
possibly with different pedigree structures - and aggregate the results by gene.

Currently, results are displayed as a list of genes,
ordered by the number of families that have candidate variants in that gene.
This means that the top of any results list almost always represents large genes and sequencing artifacts.
In the future, we plan to add more statistical context to these results,
with the goal of highlighting genes with an excess burden of potential disease variants.
In the meantime, please take care not to attribute significance to any individual result without thorough followup.

### Usage

As is standard in xBrowse, you must define the data that you want to operate on before you run an analyses.
*Combine Mendelian Families* operates on a *Family Group*,
which is just a collection of Mendelian families.
To create a Family Group, use the “Edit Families” page. Note that currently this page is only accessible to the Managers of a project.
After you create a Family Group, a link for the “Combine Mendelian Families” analysis will be available on the Family Group page.

The search interface is similar to that of *Mendelian Variant Search*, with a couple caveats:

- Only the Standard inheritance modes are available.
You can’t specify a custom genotype search, since pedigrees might be different.
So, be sure to read through the Inheritance Modes documentation, so you know exactly which variants are returned and which may be ignored.

- Like in Mendelian Variant Search, quality filters are applied to all members of a family with a known affected status (either affected or unaffected).
If *any* members of a family fail a quality filter, that variant will be ignored in this family.
However, families are considered independently, and this variant might be considered in another family if all family members pass the variant filter.

### What It Does

When you hit "Search", xBrowse literally loops through each family, runs a standard family variant search, and collects the list of genes returned.
If multiple variants exist in a gene, it is only counted once.
We often refer to this family / gene pair - with one or more contributing variants - as a "hit" in xBrowse.

### Results

As mentioned above, this search returns a list of genes.
Note that you can sort the columns of this table - sometimes you want them in genomic order,
other times in alphabetical order (though if you are sorting alphabetically you are probably doing something wrong :).
In the leftmost column, genes are highlighted if they are a known Mendelian disease gene or if they are included in a gene list.

From this results list, you can click a number of links that show pop-up windows:

- Clicking the "variants" link shows a list of variants in this gene, grouped by family.
This variants list has all the standard variant displays, including highlighting saved variants, etc.

- Clicking on the gene symbol shows the Gene Summary page.