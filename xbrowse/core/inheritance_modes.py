

INHERITANCE_DEFAULTS = [

    {
        'slug': 'recessive', 
        'name': 'Recessive', 
        'description': """This method identifies genes with any evidence of recessive variation. It is the union of all variants returned by the homozygous recessive, x-linked recessive, and compound heterozygous methods. """, 
        'datatype': 'genes', 
    },

    {
        'slug': 'homozygous_recessive', 
        'name': 'Homozygous Recessive', 
        'description': 'Finds variants where all affected individuals are Alt / Alt and each of their parents Heterozygous.', 
        'datatype': 'variants', 
    }, 

    {
        'slug': 'x_linked_recessive', 
        'name': 'X-Linked Recessive', 
        'description': "Recessive inheritance on the X Chromosome. This is similar to the homozygous recessive search, but a proband's father must be homozygous reference. (This is how hemizygous genotypes are called by current variant calling methods.)", 
        'datatype': 'variants', 
    },

    {
        'slug': 'compound_het', 
        'name': 'Compound Heterozygous', 
        'description': """
            Affected individual(s) have two heterozygous mutations in the same gene on opposite haplotypes. 
            Unaffected individuals cannot have the same combination of alleles as affected individuals, 
            or be homozygous alternate for any of the variants. 
            If parents are not present, this method only searches for pairs of heterozygous variants; they may not be on different haplotypes.
            """, 
        'datatype': 'genes', 
    },

    {
        'slug': 'dominant', 
        'name': 'Dominant', 
        'description': 'Finds variants where all affected indivs are heterozygous and all unaffected are homozygous reference.', 
        'datatype': 'variants', 
    },

    {
        'slug': 'de_novo', 
        'name': 'De Novo Dominant', 
        'description': 'Variants that fit a de novo pattern. This method currently returns the same results as dominant, although cases can be homozygous alternate. ', 
        'datatype': 'variants', 
    },

]

INHERITANCE_DEFAULTS_MAP = { item['slug']: item for item in INHERITANCE_DEFAULTS }
