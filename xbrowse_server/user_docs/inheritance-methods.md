Inheritance Methods
===

xBrowse contains a set of standard inheritance methods that identify variants that segregate with a phenotype in a family.
They are described below, but first a few notes about these methods.

- These methods rely on the *affected status* of individuals.
Individuals with an Unknown phenotype will not be considered -
so if all individuals in a family are Unknown, they will simply return all variants.
This is deliberate - as sometimes users want to load additional samples from a family alongside the
canonical variant calls for an individual (eg. from a tumor if studying familial cancers.)

- As implied by the note above, these methods only work on binary phenotypes.
In principle they could easily be extended to quantitative or probabilistic phenotypes,
but this is not applicable in a Mendelian causal variant search.

- All methods assume complete penetrance

- xBrowse assumes unphased genotypes

### Homozygous Recessive

Finds variants where all affected individuals are Alt / Alt and no unaffected individuals are Alt / Alt.
If any affected individuals have unaffected parents, the parent(s) must be heterozygous.

### X-Linked Recessive

This is similar to the homozygous recessive search, but a proband's father must be homozygous reference.
(Most current variant calling pipelines call hemizygous genotypes as homozygous).
This will also only return variants on the X Chromosome.

### Compound Heterozygous

A compound heterozygous genotype refers to a combination of two heterozygous alleles on different copies of the chromosome -
so both copies of a transcript are disrupted.
This method finds any pairs of heterozygous variants in the same gene that are present in all affected individuals,
but not in any unaffected individuals.
Additionally, no unaffected individuals can be homozygous alternate for either of the variants.

Note that if parents are present, this method implicitly considers phasing.
If not, it only searches for pairs of heterozygous variants, which may be on the same haplotype.

Finally, in some cases a gene will have multiple pairs of variants that meet the criteria above -
all variants in any pair are returned.
This can lead to odd results - for example, if you run on a family with one individual,
and that individual (unsurprisingly) has 6 heterozygous variants in TTN, all six variants are returned.

### Recessive

This method returns the union of any variants returned by the Homozygous Recessive,
X-Linked Recessive, and Compound Heterozygous searches.
It does not distinguish which variants are the result of which sub-method.

### Dominant

Finds variants where all affected individuals are heterozygous and all unaffected are homozygous reference.

### De Novo

This returns the same variants as Dominant, with one exception - affected individuals can be homozygous alternate.
