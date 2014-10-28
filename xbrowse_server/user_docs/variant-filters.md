Variant Filters
===

This page describes the different ways to filter variants in xBrowse.

### Default Filters

Since there are a variety of variant annotations - and many more under development -
we provide a few default annotation specifications, in the select box on the left of the annotation section.
If you choose one of these defaults, the form to the right will auto-populate with that filter.
If you want to clear the form, set the default to `---`. Those defaults are:

* **High Impact**: Rare nonsense splice site and frameshift mutations.

* **Moderate to High Impact**: High impact variants, plus missense and inframe mutations.

* **Rare coding variants**: Any rare coding variants, including synonymous variants.

For more details, just choose one and see what form fields are filled out.

### Filter Options

##### Functional Class

This allows you to choose a subset of functional annotations to consider.
It is an inclusive filter - it will filter *out* any variants that do not have any of the selected annotations.
(Unless no boxes are selected - then no variants are filtered out)<br>
Note that annotations are per-transcript - and this considers all annotations, not just the most severe, as some programs do.
If you select Missense, a variant with Nonsense and Missense annotations will be included.
See [Annotation](annotation) for more about xBrowse functional annotations.

##### Variant Type

A SNP is defined as a variant where the reference and alternate alleles are both one base.
An In/Del is any other variant.
This is mainly used on datasets with a high indel error rate.

##### Allele Frequency
Choose a frequency and a set of reference populations -
variants are filtered out if they have an allele frequency greater than what you've chosen in *any* of the reference populations.
Currently there is no way to specify per-population allele frequencies, though it could be added if necessary.

- There is currently no way to determine whether a 0% frequency indicates that a variant was explicitly not seen in a reference population,
or simply occurs in a genome region that was not targeted by the reference population.
We hope to support this in the next generation of reference populations, but not currently.

- We do not differentiate between Singletons and non-Singletons.
Some people want to ask "has this variant ever been seen before" -
an interesting question, but not one that should be used for filtering in a causal variant search.

- Finally, note that you can upload private reference populations of interest - see [Project Customization](project-customization).

##### Deleteriousness Predictions

These let you filter on PolyPhen and SIFT, two of the

##### Genes

##### Genomic Coordinates