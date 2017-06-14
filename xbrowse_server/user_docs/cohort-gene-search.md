Cohort Gene Search
==================

The Cohort Gene Search page provides a mechanism to search for novel disease genes in a cohort of unrelated individuals that share a rare phenotype.
One can ask whether there is a gene that is disrupted in a similar pattern - but not necessarily by the same variants -
in multiple members of the the cohort. This pattern can then be compared to a large reference panel.

### Theory
It is important to understand exactly what type of genetic architecture this method can identify.
It will only identify genes that contribute to a phenotype via highly penetrant mutations.
Conceptually, it asks whether there is a bucket of variants that, when viewed in a biological context,
is *so* interesting that it cannot be ignored.

Cohort Gene Search does not produce p-values - it should *not* be confused with traditional gene burden tests.
Burden tests can identify a statistical excess of variants in disease cohort, often in comparison to a cohort of matched controls.
While a statistical approach should always be preferred, these tests can lack power with small cohorts and high penetrance mutations.

Note that I avoid the term Mendelian here, as it carries certain implications to some. (Specifically, some assume Mendelian implies that variants must be fully penetrant, or must segregate in a pedigree - neither is strictly true for this method.) However, the variants of interest should have similar properties to the variants that cause traditional Mendelian disease.

### Data Types

This method should only be used with a very specific class of dataset:

- Cohorts should share a rare phenotype that could feasibly be caused by disruption to a single gene.
- We envision that cohorts are small - on the order of 10-50 samples. Larger samples may enable a more statistical approach.
- The cohort should not include any related individuals. Even cryptic relatedness will skew results. Currently we do not test for relatedness, though we would like to add this check in the future.

### Examples

Examples of cohorts that are appropriate to search in this manner include:

- We do not have any examples yet! This is under active development!

Popups
Gene Info
Variants
