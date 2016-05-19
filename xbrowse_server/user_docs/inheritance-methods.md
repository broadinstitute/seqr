Inheritance Searching
===

_seqr_ implements a set of standard Mendelian inheritance methods to identify variants that segregate with a phenotype in a family.
These filters are described in detail below, but first a few notes about these methods.

- These methods rely on the *affected status* of individuals.
Individuals with an Unknown phenotype will not be considered -
so if all individuals in a family are Unknown, they will simply return all variants.

- All methods assume complete penetrance

- seqr assumes unphased genotypes

### *Homozygous Recessive* 

Returns variants where all affected individuals have two copies of the same alternate allele at a specific postion (Alt/Alt genotype) and all unaffected individuals have at least one reference allele at this position. If parents are present, it is required that they be heterozygous at this location.

### *Compound Heterozygous*

A compound heterozygous genotype refers to two non-reference alleles each on different copies of the same gene, thus predicted to disrupt both copies of the gene.

This method finds any pairs of heterozygous variants in the same gene that are present in all affected individuals,
but not in any unaffected individuals.
Additionally, no unaffected individuals can be homozygous alternate for either of the variants.

Note that if parents are present, this method implicitly considers phasing. If not, it searches for pairs of heterozygous variants and cannot determine if they are on different copies of the gene.

In some cases multiple pairs of variants in a gene will meet the above criteria, meaning there is a chance more than two variants in a gene would be returned.


### *X-Linked Recessive*

This filter returns variants where indivduals are homozygous variant for a mutation on the X chromosome. Unaffected fathers will always appear homozygous reference (Most current variant calling pipelines call hemizygous genotypes as homozygous, but they in fact have only one allele at this position because they have one copy of the X chromosome). Affected sons need only inherit one alt allele from their mother and will appear homozygous alt at these positions. Variants will only pass this filter if they are  homozygous alt in  affected individuals.


### *Recessive*

This method returns all  variants passing the Homozygous Recessive,
X-Linked Recessive, and Compound Heterozygous filtration parameters.
The results do not distinguish which variants are the result of which sub-method, but this can be determined by patient genotype.

### *Dominant*

Finds variants where all affected individuals are heterozygous and all unaffected individuals are homozygous reference.

### *De Novo*

This search should only be conducted in cases where parental data is available. It will return locations where unaffected parents are homozygous reference and affected children are heterozygous.

