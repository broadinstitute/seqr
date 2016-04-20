Inheritance Searching
===

seqr contains a set of standard inheritance methods that identify variants that segregate with a phenotype in a family.
They are described below, but first a few notes about these methods.

- These methods rely on the *affected status* of individuals.
Individuals with an Unknown phenotype will not be considered -
so if all individuals in a family are Unknown, they will simply return all variants.

- All methods assume complete penetrance

- seqr assumes unphased genotypes

### Homozygous Recessive 

Returns variants where all affected individuals are Alt / Alt and all unaffected parents are heterozygous. No unaffected individuals are Alt / Alt.

### Compound Heterozygous

A compound heterozygous genotype refers to two heterozygous alleles on different copies of the same gene, thus disrupting both copies of the transcript.
This method finds any pairs of heterozygous variants in the same gene that are present in all affected individuals,
but not in any unaffected individuals.
Additionally, no unaffected individuals can be Alt / Alt for either of the variants.

Note that if parents are present, this method implicitly considers phasing. If not, it only searches for pairs of heterozygous variants, which may be on the same haplotype.

Finally, in some cases a gene will have multiple pairs of variants that meet the criteria above -
all variants in any pair are returned.
This can lead to odd results - for example, if you run on a family with one individual,
and that individual has 6 heterozygous variants in TTN, all six variants are returned.

### X-Linked Recessive

Similar to the homozygous recessive search, this filter returns cases where indivduals are homozygous variant for a mutation on the X chromosome. Unaffected fathers will always appear homozygous reference (Most current variant calling pipelines call hemizygous genotypes as homozygous, but they in fact have only one allele at this position because they have one copy of the X chromosome). Affected sons need only inherit one alt allele from their mother. In most cases, Females will only present with a phenotype if they have two alt alleles


### Recessive

This method returns the union of any variants returned by the Homozygous Recessive,
X-Linked Recessive, and Compound Heterozygous searches.
It does not distinguish which variants are the result of which sub-method.

### Dominant

Finds variants where all affected individuals are heterozygous and all unaffected are homozygous reference.

### De Novo

This returns the same variants as Dominant, with one exception - affected individuals can be homozygous alternate.
