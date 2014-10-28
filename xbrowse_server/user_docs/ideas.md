This is kind of my sandbox for recording random ideas that may be implemented

### Reducing Variants

Goal is to avoid the case where one vcf file has ref/alt of AT/ATT
and another has T/TT

- Should we use VCF or ensembl coordinates (ie. should base before the insertion be included)

- What about when ref is AAA and alt AA - how do you decide which position?
Do we really need to look at sequence context?

### Simplified Server Datastore

- rename mongo_datastore to server_datastore
- contains a mongodb connection
- collections:
    - snp_arrays
    - family_123
    - cohort_456
