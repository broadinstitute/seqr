Mendelian Variant Search
===

[In progress]

*Mendelian Variant Search* is the canonical xBrowse search interface,
where you can search for potential causal variants from the the variant calls in a family.

This page aims to provide a fast, intuitive, and flexible interface for researchers to identify and interpret variants in a family.
Note that it does not automatically prioritize causal variants - interpretation is left to the researcher.

## Usage

Each "search" in Mendelian Variant Search is a single query -
for example, *are there any loss of function de novo variants in this trio?*.
A search is composed of a few different parts, which are separated into sections in the search interface.
These are described below:

### Inheritance

This section provides controls for choosing which inheritance mode to explore.
There are two ways to specify an inheritance:

##### Default Inheritance Modes

A set of default methods for specifying inheritance in a family.
These are described in [Inheritance Methods](inheritance-methods).

##### Manual Genotype Filter

Here you can specify an inheritance pattern yourself - which family members should have what genotypes.
You'll notice in the genotype select box that there are two types of genotypes - *Individual Genotype* and *# Alleles In Gene*.

*Individual Genotype* is a simple genotype specification - for example, that individual A should be heterozygous.

*# Alleles In Gene* is a property of a gene - it allows you to search for genes based on how many alternate alleles an individual has in that gene.
*2 or more* can refer to a single homozygous alternate genotype or two heterozygous genotypes.

If you just want to see all the variants in a family that meet a particular variant filter (see below) -
choose Custom and don't specify any genotypes.

### Variant Annotations

Here you specify which classes of variation you are interested in.
These are described in [Variant Filters](variant-filters).

### Results

Hopefully not too long after you click Search, a list of variants will appear at the bottom of the page -
the results of your search.

A few things to know about this table of variants:

- Make sure you scroll the table all the way to the right - the table will usually be wider than your screen.

- Many of the fields are links. Links with a <i class="icon-external-link-sign"></i>
after them open a new tab and go to an external page.
Other links open up a "Modal" window within xBrowse to display more details.

- Click on the gear icon (<i class="icon-gear"></i>) to save a variant.
Note that you can only save one variant at a time - so to save a compound heterozygous variant pair,
unfortunately must save both variants separately.
