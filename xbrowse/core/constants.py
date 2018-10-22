# DELETE THIS FILE
# most of this stuff belongs on the server

import copy

GENOME_VERSION_GRCh37 = '37'
GENOME_VERSION_GRCh38 = '38'

GENOTYPE_OPTIONS = [

    {
        'name': 'Homozygous Reference',
        'short_name': 'Ref / Ref',
        'slug': 'ref_ref',
        'granularity': 'variant',
        'exact_genotype': True,
        'description': 'Two reference alleles'
    },

    {
        'name': 'Heterozygous',
        'short_name': 'Het',
        'slug': 'ref_alt',
        'granularity': 'variant',
        'exact_genotype': True,
        'description': 'One reference allele and one alternate allele'
    },

    {
        'name': 'Homozygous Alternate',
        'short_name': 'Alt / Alt',
        'slug': 'alt_alt',
        'granularity': 'variant',
        'exact_genotype': True,
        'description': """
            Two alternate alleles. Note that this may not be the minor allele, in cases where the reference
            genome is "wrong". We are working on moving to minor alleles by default.
        """,
    },

    {
        'name': 'Missing',
        'short_name': 'Missing',
        'slug': 'missing',
        'granularity': 'variant',
        'exact_genotype': True,
        'description': """
            Genotype is missing, ie. a variant call was attempted but failed.
            We do not consider the case of one allele called and the other missing -- in this case, the
            whole genotype is missing.
        """,
    },

    {
        'name': 'At least one alt allele',
        'short_name': '>1 alt',
        'slug': 'has_alt',
        'granularity': 'variant',
        'exact_genotype': False,
        'description': """
            Union of homozygous alternate and heterozygous cases above.
        """,
    },

    {
        'name': 'At least one ref allele',
        'short_name': '>1 ref',
        'slug': 'has_ref',
        'granularity': 'variant',
        'exact_genotype': False,
        'description': """
            Union of homozygous reference and heterozygous cases above.
        """,
    },

]

BURDEN_FILTER_OPTIONS = [
    {
        'slug': 'at_least_1',
        'name': '1 or more alt alleles',
    },
    {
        'slug': 'at_least_2',
        'name': '2 or more alt alleles',
    },
    {
        'slug': 'less_than_2',
        'name': 'Less than 2 alt alleles',
    },
    {
        'slug': 'none',
        'name': 'No alt alleles',
    },
]

# TODO: get rid of these
QUERY_DEFAULTS = {

    'high_impact': {

        'effects.vep': { '$in': [
            'pathogenic',
            'likely_pathogenic',
            'disease_causing',
            'likely_disease_causing',
            'stop_gained',
            'splice_donor_variant',
            'splice_acceptor_variant',
            'frameshift_variant',

        ]},

        'ESP_EA_AF': { '$lte': 0.01 },
        'ESP_AA_AF': { '$lte': 0.01 },
        'ATGU_CONTROLS_AF': { '$lte': 0.01 },
        'AF': { '$lte': 0.01 },

    },

    'moderate_impact': {

        'effects.vep': { '$in': [
            'pathogenic',
            'likely_pathogenic',
            'disease_causing',
            'likely_disease_causing',
            'stop_gained',
            'splice_donor_variant',
            'splice_acceptor_variant',

            'stop_lost',
            'initiator_codon_variant',
            'start_lost',
            'missense_variant',

            'frameshift_variant',
            'inframe_insertion',
            'inframe_deletion',
            'protein_altering_variant',

        ]},

        'ESP_EA_AF': { '$lte': 0.01 },
        'ESP_AA_AF': { '$lte': 0.01 },
        'ATGU_CONTROLS_AF': { '$lte': 0.01 },
        'AF': { '$lte': 0.01 },

    },

    'all_coding': {

        'effects.vep': { '$in': [
            'pathogenic',
            'likely_pathogenic',
            'disease_causing',
            'likely_disease_causing',
            'stop_gained',
            'splice_donor_variant',
            'splice_acceptor_variant',
            'splice_region_variant',

            'stop_lost',
            'initiator_codon_variant',
            'start_lost',
            'missense_variant',

            'frameshift_variant',
            'inframe_insertion',
            'inframe_deletion',
            'protein_altering_variant',

            'synonymous_variant',
            'stop_retained_variant',

            'splice_region_variant',


        ]},

        'ESP_EA_AF': { '$lte': 0.01 },
        'ESP_AA_AF': { '$lte': 0.01 },
        'ATGU_CONTROLS_AF': { '$lte': 0.01 },
        'AF': { '$lte': 0.01 },

    },

}

ANNOTATIONS = [

    'nonsense',
    'splice',
    'missense',
    'silent',
    'none',
    'frameshift',
    'inframe',

]

CLINVAR_ANNOTATION_DEFINITIONS = [
    {'description': "Clinvar pathogenic variant",
     'name': 'Pathogenic (P)',
     'slug': 'pathogenic',
     'so': 'pathogenic',
     },
    {'description': "Clinvar likely pathogenic variant",
     'name': 'Likely Pathogenic (LP)',
     'slug': 'likely_pathogenic',
     'so': 'likely_pathogenic',
     },
    {'description': "Clinvar variant of uncertain significance or variant with conflicting interpretations",
     'name': 'VUS or Conflicting',
     'slug': 'vus_or_conflicting',
     'so': 'vus_or_conflicting',
     },
    {'description': "Clinvar likely benign variant",
     'name': 'Likely Benign (LB)',
     'slug': 'likely_benign',
     'so': 'likely_benign',
     },
    {'description': "Clinvar benign variant",
     'name': 'Benign (B)',
     'slug': 'benign',
     'so': 'benign',
     },
]

HGMD_ANNOTATION_DEFINITIONS = [
    {'description': "HGMD: Pathological mutation reported to be disease causing in the corresponding report (i.e. all other HGMD data).",
     'name': 'Disease Causing (DM)',
     'slug': 'disease_causing',
     'so': 'disease_causing',
     },
    {'description': "HGMD: Likely pathological mutation reported to be disease causing in the corresponding report, but where the author has indicated that there may be some degree of doubt, or subsequent evidence has come to light in the literature, calling the deleterious nature of the variant into question.",
     'name': 'Likely Disease Causing (DM?)',
     'slug': 'likely_disease_causing',
     'so': 'likely_disease_causing',
     },
    {'description': "HGMD: All other classifications present in HGMD (including: Disease-associated polymorphism (DP), Disease-associated polymorphism with additional supporting functional evidence (DFP), In vitro/laboratory or in vivo functional polymorphism (FP), Frameshift or truncating variant (FTV)",
     'name': 'Other (DP, DFP, FP, FTV)',
     'slug': 'hgmd_other',
     'so': 'hgmd_other',
     },
]

VEP_ANNOTATION_DEFINITIONS = [

    {'description': "A splice variant that changes the 2 base region at the 5' end of an intron",
     'name': 'Splice donor variant',
     'slug': 'splice_donor_variant',
     'so': 'SO:0001575'},

    {'description': "A splice variant that changes the 2 base region at the 3' end of an intron",
    'name': 'Splice acceptor variant',
    'slug': 'splice_acceptor_variant',
    'so': 'SO:0001574'},

    {'description': 'A sequence variant in which a change has occurred within the region of the splice site, either within 1-3 bases of the exon or 3-8 bases of the intron',
    'name': 'Splice region',
    'slug': 'splice_region_variant',
    'so': 'SO:0001630'},

    {'description': 'A sequence variant whereby at least one base of a codon is changed, resulting in a premature stop codon, leading to a shortened transcript',
    'name': 'Stop gained',
    'slug': 'stop_gained',
    'so': 'SO:0001587'},

    {'description': 'A sequence variant where at least one base of the terminator codon (stop) is changed, resulting in an elongated transcript',
    'name': 'Stop lost',
    'slug': 'stop_lost',
    'so': 'SO:0001578'},

    {'description': 'A codon variant that changes at least one base of the first codon of a transcript',
    'name': 'Initiator codon',
    'slug': 'initiator_codon_variant',
    'so': 'SO:0001582'},

    {'description': 'A codon variant that changes at least one base of the canonical start codon.',
    'name': 'Start lost',
    'slug': 'start_lost',
    'so': 'SO:0002012'},

    {'description': 'A sequence variant, where the change may be longer than 3 bases, and at least one base of a codon is changed resulting in a codon that encodes for a different amino acid',
    'name': 'Missense',
    'slug': 'missense_variant',
    'so': 'SO:0001583'},

    {'description': 'A sequence variant which causes a disruption of the translational reading frame, because the number of nucleotides inserted or deleted is not a multiple of three',
    'name': 'Frameshift',
    'slug': 'frameshift_variant',
    'so': 'SO:0001589'},

    {'description': 'A sequence_variant which is predicted to change the protein encoded in the coding sequence',
    'name': 'Protein Altering',
    'slug': 'protein_altering_variant',
    'so': 'SO:0001818'},

    {'description': 'An inframe non synonymous variant that inserts bases into in the coding sequence',
    'name': 'In frame insertion',
    'slug': 'inframe_insertion',
    'so': 'SO:0001821'},

    {'description': 'An inframe non synonymous variant that deletes bases from the coding sequence',
    'name': 'In frame deletion',
    'slug': 'inframe_deletion',
    'so': 'SO:0001822'},

    {'description': 'A sequence variant where there is no resulting change to the encoded amino acid',
    'name': 'Synonymous',
    'slug': 'synonymous_variant',
    'so': 'SO:0001819'},

    {'description': 'A sequence variant where at least one base in the terminator codon is changed, but the terminator remains',
    'name': 'Stop retained',
    'slug': 'stop_retained_variant',
    'so': 'SO:0001567'},

    {'description': 'A feature ablation whereby the deleted region includes a transcript feature',
    'name': 'Transcript ablation',
    'slug': 'transcript_ablation',
    'so': 'SO:0001893'},

    {'description': 'A feature amplification of a region containing a transcript',
    'name': 'Transcript amplification',
    'slug': 'transcript_amplification',
    'so': 'SO:0001889'},
    {'description': 'A sequence variant where at least one base of the final codon of an incompletely annotated transcript is changed',
    'name': 'Incomplete terminal codon variant',
    'slug': 'incomplete_terminal_codon_variant',
    'so': 'SO:0001626'},

    {'description': 'A sequence variant that changes the coding sequence',
    'name': 'coding_sequence_variant',
    'slug': 'coding_sequence_variant',
    'so': 'SO:0001580'},
    {'description': 'A transcript variant located with the sequence of the mature miRNA',
    'name': 'mature_miRNA_variant',
    'slug': 'mature_miRNA_variant',
    'so': 'SO:0001620'},
    {'description': "A UTR variant of the 5' UTR",
    'name': '5_prime_UTR_variant',
    'slug': '5_prime_UTR_variant',
    'so': 'SO:0001623'},
    {'description': "A UTR variant of the 3' UTR",
    'name': '3_prime_UTR_variant',
    'slug': '3_prime_UTR_variant',
    'so': 'SO:0001624'},
    {'description': 'A transcript variant occurring within an intron',
    'name': 'intron_variant',
    'slug': 'intron_variant',
    'so': 'SO:0001627'},
    {'description': 'A variant in a transcript that is the target of NMD',
    'name': 'NMD_transcript_variant',
    'slug': 'NMD_transcript_variant',
    'so': 'SO:0001621'},

    # 2 kinds of 'non_coding_transcript_exon_variant' label due to name change in Ensembl v77
    {'description': 'A sequence variant that changes non-coding exon sequence',
    'name': 'non_coding_exon_variant',
    'slug': 'non_coding_exon_variant',
    'so': 'SO:0001792'},
    {'description': 'A sequence variant that changes non-coding exon sequence',
     'name': 'non_coding_transcript_exon_variant',
     'slug': 'non_coding_transcript_exon_variant',
     'so': 'SO:0001792'},

    # 2 kinds of 'nc_transcript_variant' label due to name change in Ensembl v77
    {'description': 'A transcript variant of a non coding RNA',
    'name': 'nc_transcript_variant',
    'slug': 'nc_transcript_variant',
    'so': 'SO:0001619'},
    {'description': 'A transcript variant of a non coding RNA',
     'name': 'non_coding_transcript_variant',
     'slug': 'non_coding_transcript_variant',
     'so': 'SO:0001619'},

    {'description': "A sequence variant located 5' of a gene",
    'name': 'upstream_gene_variant',
    'slug': 'upstream_gene_variant',
    'so': 'SO:0001631'},
    {'description': "A sequence variant located 3' of a gene",
    'name': 'downstream_gene_variant',
    'slug': 'downstream_gene_variant',
    'so': 'SO:0001632'},
    {'description': 'A feature ablation whereby the deleted region includes a transcription factor binding site',
    'name': 'TFBS_ablation',
    'slug': 'TFBS_ablation',
    'so': 'SO:0001895'},
    {'description': 'A feature amplification of a region containing a transcription factor binding site',
    'name': 'TFBS_amplification',
    'slug': 'TFBS_amplification',
    'so': 'SO:0001892'},
    {'description': 'In regulatory region annotated by Ensembl',
    'name': 'TF_binding_site_variant',
    'slug': 'TF_binding_site_variant',
    'so': 'SO:0001782'},
    {'description': 'A sequence variant located within a regulatory region',
    'name': 'regulatory_region_variant',
    'slug': 'regulatory_region_variant',
    'so': 'SO:0001566'},
    {'description': 'A feature ablation whereby the deleted region includes a regulatory region',
    'name': 'regulatory_region_ablation',
    'slug': 'regulatory_region_ablation',
    'so': 'SO:0001894'},
    {'description': 'A feature amplification of a region containing a regulatory region',
    'name': 'regulatory_region_amplification',
    'slug': 'regulatory_region_amplification',
    'so': 'SO:0001891'},
    {'description': 'A sequence variant that causes the extension of a genomic feature, with regard to the reference sequence',
    'name': 'feature_elongation',
    'slug': 'feature_elongation',
    'so': 'SO:0001907'},
    {'description': 'A sequence variant that causes the reduction of a genomic feature, with regard to the reference sequence',
    'name': 'feature_truncation',
    'slug': 'feature_truncation',
    'so': 'SO:0001906'},
    {'description': 'A sequence variant located in the intergenic region, between genes',
    'name': 'intergenic_variant',
    'slug': 'intergenic_variant',
    'so': 'SO:0001628'},
]

ANNOTATION_DEFINITIONS = CLINVAR_ANNOTATION_DEFINITIONS + VEP_ANNOTATION_DEFINITIONS
ANNOTATION_DEFINITIONS_INTERNAL = CLINVAR_ANNOTATION_DEFINITIONS + HGMD_ANNOTATION_DEFINITIONS + VEP_ANNOTATION_DEFINITIONS


ANNOTATION_DEFINITIONS_MAP = { item['slug']: item for item in ANNOTATION_DEFINITIONS }
ANNOTATION_DEFINITIONS_MAP_INTERNAL = { item['slug']: item for item in ANNOTATION_DEFINITIONS_INTERNAL }

CLINVAR_ANNOTATION_GROUPS = [
    {
        'name': 'In Clinvar',
        'slug': 'clinvar',
        'children': [
            'pathogenic',
            'likely_pathogenic',
            'vus_or_conflicting',
            'likely_benign',
            'benign',
        ]
    },
]

HGMD_ANNOTATION_GROUPS = [
    {
        'name': 'In HGMD',
        'slug': 'hgmd',
        'children': [   # see https://portal.biobase-international.com/hgmd/pro/global.php#cats
            'disease_causing',
            'likely_disease_causing',
            'hgmd_other',
        ]
    },
]

VEP_ANNOTATION_GROUPS = [
    {
        'name': 'Nonsense',
        'slug': 'nonsense',
        'children': [
            'stop_gained',
        ]
    },
    {
        'name': 'Essential splice site',
        'slug': 'essential_splice_site',
        'children': [
            'splice_donor_variant',
            'splice_acceptor_variant'
        ],
    },

    {
        'name': 'Extended splice site',
        'slug': 'extended_splice_site',
        'children': [
            'splice_region_variant',
        ],
    },

    {
        'name': 'Missense',
        'slug': 'missense',
        'children': [

            'stop_lost',
            'initiator_codon_variant',
            'start_lost',
            'missense_variant',
            'protein_altering_variant',
        ],
    },

    {
        'name': 'Frameshift',
        'slug': 'frameshift',
        'children': [
            'frameshift_variant',
        ]
    },

    {
        'name': 'In Frame',
        'slug': 'inframe',
        'children': [
            'inframe_insertion',
            'inframe_deletion',
        ]
    },

    {
        'name': 'Synonymous',
        'slug': 'synonymous',
        'children': [
            'synonymous_variant',
            'stop_retained_variant',
        ]
    },

    {

        'name': 'Other',
        'slug': 'other',
        'children': [

            'transcript_ablation',
            'transcript_amplification',
            'incomplete_terminal_codon_variant',
            'coding_sequence_variant',
            'mature_miRNA_variant',
            '5_prime_UTR_variant',
            '3_prime_UTR_variant',
            'intron_variant',
            'NMD_transcript_variant',
            'non_coding_exon_variant',  # 2 kinds of 'non_coding_exon_variant' label due to name change in Ensembl v77
            'non_coding_transcript_exon_variant',  # 2 kinds of 'non_coding_exon_variant' due to name change in Ensembl v77
            'nc_transcript_variant',  # 2 kinds of 'nc_transcript_variant' label due to name change in Ensembl v77
            'non_coding_transcript_variant',  # 2 kinds of 'nc_transcript_variant' due to name change in Ensembl v77
            'upstream_gene_variant',
            'downstream_gene_variant',
            'TFBS_ablation',
            'TFBS_amplification',
            'TF_binding_site_variant',
            'regulatory_region_variant',
            'regulatory_region_ablation',
            'regulatory_region_amplification',
            'feature_elongation',
            'feature_truncation',
            'intergenic_variant',

        ]
    }
]


ANNOTATION_GROUPS = CLINVAR_ANNOTATION_GROUPS + VEP_ANNOTATION_GROUPS
ANNOTATION_GROUPS_INTERNAL = CLINVAR_ANNOTATION_GROUPS + HGMD_ANNOTATION_GROUPS + VEP_ANNOTATION_GROUPS

ANNOTATION_GROUPS_MAP = { item['slug']: item for item in ANNOTATION_GROUPS }
ANNOTATION_GROUPS_MAP_INTERNAL = { item['slug']: item for item in ANNOTATION_GROUPS_INTERNAL }

ANNOTATION_DEFINITIONS_GROUPED = copy.deepcopy(ANNOTATION_GROUPS)
for group in ANNOTATION_DEFINITIONS_GROUPED:
   group['children'] = [ ANNOTATION_DEFINITIONS_MAP[item] for item in group['children'] ]

ANNOTATION_DEFINITIONS_GROUPED_INTERNAL = copy.deepcopy(ANNOTATION_GROUPS_INTERNAL)
for group in ANNOTATION_DEFINITIONS_GROUPED_INTERNAL:
    group['children'] = [ ANNOTATION_DEFINITIONS_MAP_INTERNAL[item] for item in group['children'] ]

ANNOTATION_GROUP_REVERSE_MAP = {}
for group in ANNOTATION_GROUPS:
    for child in group['children']:
        ANNOTATION_GROUP_REVERSE_MAP[child] = group['slug']

ANNOTATION_GROUP_REVERSE_MAP_INTERNAL = {}
for group in ANNOTATION_GROUPS_INTERNAL:
    for child in group['children']:
        ANNOTATION_GROUP_REVERSE_MAP_INTERNAL[child] = group['slug']


ANNOTATION_REFERENCE = {
    'definitions': ANNOTATION_DEFINITIONS,
    'definitions_map': ANNOTATION_DEFINITIONS_MAP,
    'groups': ANNOTATION_GROUPS,
    'groups_map': ANNOTATION_GROUPS_MAP,
    'reverse_map': ANNOTATION_GROUP_REVERSE_MAP,
    'definitions_grouped': ANNOTATION_DEFINITIONS_GROUPED,
}

ANNOTATION_REFERENCE_INTERNAL = {
    'definitions': ANNOTATION_DEFINITIONS_INTERNAL,
    'definitions_map': ANNOTATION_DEFINITIONS_MAP_INTERNAL,
    'groups': ANNOTATION_GROUPS_INTERNAL,
    'groups_map': ANNOTATION_GROUPS_MAP_INTERNAL,
    'reverse_map': ANNOTATION_GROUP_REVERSE_MAP_INTERNAL,
    'definitions_grouped': ANNOTATION_DEFINITIONS_GROUPED_INTERNAL,
}

TISSUE_TYPES = [
    {
        'name': 'Adipose Tissue',
        'slug': 'adipose_tissue',
    },
    {
         'name': 'Adrenal Gland',
         'slug': 'adrenal_gland',
    },
    #{
    #     'name': 'Bladder',
    #     'slug': 'bladder',
    #},
    {
        'name': 'Whole Blood',
        'slug': 'whole_blood',
    },
    {
        'name': 'Cells: Lymphocytes',
        'slug': 'cells_-_ebv-transformed_lymphocytes',
    },
    {
        'name': 'Blood Vessel',
        'slug': 'blood_vessel',
    },
    #{
    #    'name': 'Cells: Leukemia cells (CML)',
    #    'slug': 'cells_-_leukemia_cell_line_(cml)',
    #},
    {
        'name': 'Brain',
        'slug': 'brain',
    },
    {
        'name': 'Breast',
        'slug': 'breast',
    },
#    {
#         'name': 'Cervix Uteri',
#         'slug': 'cervix_uteri',
#    },
    {
         'name': 'Colon',
         'slug': 'colon',
    },
    {
         'name': 'Esophagus',
         'slug': 'esophagus',
    },
#    {
#         'name':  'Fallopian Tube',
#         'slug':  'fallopian_tube',
#    },
    {
        'name': 'Heart',
        'slug': 'heart',
    },
    {
        'name': 'Liver',
        'slug': 'liver',
    },
    {
         'name': 'Kidney',
         'slug': 'kidney',
    },
    {
        'name': 'Lung',
        'slug': 'lung',
    },
    {
        'name': 'Muscle',
        'slug': 'muscle',
    },
    {
        'name': 'Nerve',
        'slug': 'nerve',
    },
    {
        'name': 'Pancreas',
        'slug': 'pancreas',
    },
    {
         'name': 'Ovary',
         'slug': 'ovary',
    },
    {
        'name': 'Pituitary',
        'slug': 'pituitary',
    },
    {
        'name': 'Prostate',
        'slug': 'prostate',
    },
    {
         'name': 'Salivary Gland',
         'slug': 'salivary_gland',
    },
    {
        'name': 'Cells: Fibroblasts',
        'slug': 'cells_-_transformed_fibroblasts',
    },
    {
        'name': 'Skin',
        'slug': 'skin',
    },
    {
         'name':  'Small Intestine',
         'slug':  'small_intestine',
    },
    {
         'name':  'Spleen',
         'slug':  'spleen',
    },
    {
         'name': 'Stomach',
         'slug': 'stomach',
    },
    {
         'name': 'Testis',
         'slug': 'testis',
    },
    {
        'name': 'Thyroid',
        'slug': 'thyroid',
    },
    {
        'name': 'Uterus',
        'slug': 'uterus',
    },
    {
        'name': 'Vagina',
        'slug': 'vagina',
    },
]


EXPRESSION_REFERENCE = {
    'tissue_types': TISSUE_TYPES,
}

GENE_REFERENCE = {
    'gene_stats': [

        {
            'slug': 'gene_size',
            'name': 'Gene size',
            'desc': 'Total gene size in Kb, includes all noncoding region',
            'type': 'genome_size',
        },

        {
            'slug': 'coding_size',
            'name': 'Coding region size',
            'desc': 'Sum of sizes of all coding exons, in Kb',
            'type': 'genome_size',
        },

        {
            'slug': 'num_transcripts',
            'name': 'Number of transcripts',
            'desc': 'Number of transcripts',
            'type': 'quantity'
        },

        {
            'slug': 'num_coding_transcripts',
            'name': 'Number of coding transcripts',
            'desc': 'Number of protein coding transcripts',
            'type': 'quantity'
        },

        {
            'slug': 'num_variants',
            'name': 'Number of variants in ESP dataset',
            'desc': """
                Total number of variants in ESP reference dataset.
                This is variant count, not allele count, so common variants and singletons are weighted equally.
                Also note the ratio of num variants:gene size cannot necessarily be compared across genes, because the amount coverered by exome seuqencing tarets will vary by gene.
                Use this ratio in coding regions instead.
            """,
            'type': 'quantity'
        },

        {
            'slug': 'num_coding_variants',
            'name': 'Number of ESP variants in coding regions',
            'desc': 'Same as above, but only including those in coding regions.',
            'type': 'quantity'
        },

        {
            'slug': 'num_alt_alleles',
            'name': 'Number of alt alleles in ESP',
            'desc': 'Total number of alt alleles in all 6500 ESP reference samples. ',
            'type': 'quantity'
        },

        {
            'slug': 'num_coding_alt_alleles',
            'name': 'Number of alt alleles in coding regions in ESP',
            'desc': 'Same as above, for variants in coding regions',
            'type': 'quantity'
        },

        {
            'slug': 'mean_frequency',
            'name': 'Mean allele frequency',
            'desc': """This is the mean allele frequency for all alt alleles in ESP.
                If all samples were perfectly called this would be equal to num alleles / num variants above, but it is often higher, as common variants are called more frequently than rare variants.
                *Note*: I am worried this is unhelpful and misleading, so will probably be changing it.
            """,
            'type': 'frequency'
        },

        {
            'slug': 'mean_coding_frequency',
            'name': 'Mean allele frequency in coding regions',
            'desc': 'Same as above, for coding regions. *See warning above*',
            'type': 'frequency'
        },

    ]
}


CHROMOSOME_SIZES = {
    "1":249250621,
    "2":243199373,
    "3":198022430,
    "4":191154276,
    "5":180915260,
    "6":171115067,
    "7":159138663,
    "8":146364022,
    "9":141213431,
    "10":135534747,
    "11":135006516,
    "12":133851895,
    "13":115169878,
    "14":107349540,
    "15":102531392,
    "16":90354753,
    "17":81195210,
    "18":78077248,
    "19":59128983,
    "20":63025520,
    "21":48129895,
    "22":51304566,
    "X":155270560,
    "Y":59373566,
    "MT":16569,
}

FUNCTIONAL_DATA_TAGS = [
    {
        'tag': 'Biochemical Function',
        'metadata_title': 'Notes',
        'metadata_input_props': 'maxlength="50" style="width:400px"',
        'description': 'Gene product performs a biochemical function shared with other known genes in the disease of interest, or consistent with the phenotype.',
        'color': '#311B92',
        'category': 'Functional Data',
    },
    {
        'tag': 'Protein Interaction',
        'metadata_title': 'Notes',
        'metadata_input_props': 'maxlength="50" style="width:400px"',
        'description': 'Gene product interacts with proteins previously implicated (genetically or biochemically) in the disease of interest.',
        'color': '#4A148C',
        'category': 'Functional Data',
    },
    {
        'tag': 'Expression',
        'metadata_title': 'Notes',
        'metadata_input_props': 'maxlength="50" style="width:400px"',
        'description': 'Gene is expressed in tissues relevant to the disease of interest and/or is altered in expression in patients who have the disease.',
        'color': '#7C4DFF',
        'category': 'Functional Data',
    },
    {
        'tag': 'Patient Cells',
        'metadata_title': 'Notes',
        'metadata_input_props': 'maxlength="50" style="width:400px"',
        'description': 'Gene and/or gene product function is demonstrably altered in patients carrying candidate mutations.',
        'color': '#B388FF',
        'category': 'Functional Data',
    },
    {
        'tag': 'Non-patient cells',
        'metadata_title': 'Notes',
        'metadata_input_props': 'maxlength="50" style="width:400px"',
        'description': 'Gene and/or gene product function is demonstrably altered in human cell culture models carrying candidate mutations.',
        'color': '#9575CD',
        'category': 'Functional Data',
    },
    {
        'tag': 'Animal Model',
        'metadata_title': 'Notes',
        'metadata_input_props': 'maxlength="50" style="width:400px"',
        'description': 'Non-human animal models with a similarly disrupted copy of the affected gene show a phenotype consistent with human disease state.',
        'color': '#AA00FF',
        'category': 'Functional Data',
    },
    {
        'tag': 'Non-human cell culture model',
        'metadata_title': 'Notes',
        'metadata_input_props': 'maxlength="50" style="width:400px"',
        'description': 'Non-human cell-culture models with a similarly disrupted copy of the affected gene show a phenotype consistent with human disease state.',
        'color': '#BA68C8',
        'category': 'Functional Data',
    },
    {
        'tag': 'Rescue',
        'metadata_title': 'Notes',
        'metadata_input_props': 'maxlength="50" style="width:400px"',
        'description': 'The cellular phenotype in patient-derived cells or engineered equivalents can be rescued by addition of the wild-type gene product.',
        'color': '#663399',
        'category': 'Functional Data',
    },
    {
        'tag': 'Genome-wide Linkage',
        'metadata_title': 'LOD Score',
        'metadata_input_props': 'type="number" required="true" style="width:120px;"',
        'description': 'Max LOD score used in analysis to restrict where you looked for causal variants; provide best score available, whether it be a cumulative LOD score across multiple families or just the best family\'s LOD score.',
        'color': '#880E4F',
        'category': 'Functional Scores',
    },
    {
        'tag': 'Bonferroni corrected p-value',
        'metadata_title': 'P-value',
        'metadata_input_props': 'type="number" required="true" style="width:120px;"',
        'description': 'Bonferroni-corrected p-value for gene if association testing/burden testing/etc was used to identify the gene.',
        'color': '#E91E63',
        'category': 'Functional Scores',
    },
    {
        'tag': 'Kindreds w/ Overlapping SV & Similar Phenotype',
        'metadata_title': '#',
        'metadata_input_props': 'type="number" required="true" style="width:120px;"',
        'description': 'Number of kindreds (1+) previously reported/in databases as having structural variant overlapping the gene and a similar phenotype.',
        'color': '#FF5252',
        'category': 'Functional Scores',
    },
    {
        'tag': 'Additional Unrelated Kindreds w/ Causal Variants in Gene',
        'metadata_title': '# additional families',
        'metadata_input_props': 'type="number" required="true" style="width:120px;"',
        'description': 'Number of additional kindreds with causal variants in this gene (Any other kindreds from collaborators, MME, literature etc). Do not count your family in this total.',
        'color': '#D84315',
        'category': 'Additional Kindreds (Literature, MME)',
    }
]


REFERENCE_DATA_FILES = {
    'gencode': 'gencode.v27lift37.annotation.gtf.gz',
    'high_variability_genes': 'high_variability.genes.txt',
    'constraint_scores': 'constraint_scores.csv',
    'gtex_expression': 'GTEx_Analysis_v6_RNA-seq_RNA-SeQCv1.1.8_gene_rpkm.gct.gz',
    'gtex_samples': 'GTEx_Data_V6_Annotations_SampleAttributesDS.txt',
    'omim_genmap': 'omim/genemap2.txt',
    'clinvar': 'clinvar.tsv',
    'dbnsfp': 'dbNSFP3.5_gene'
}
