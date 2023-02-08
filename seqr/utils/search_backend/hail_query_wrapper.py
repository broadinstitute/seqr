from copy import deepcopy
from collections import defaultdict
import hail as hl
import logging

from seqr.views.utils.json_utils import _to_camel_case
from reference_data.models import GENOME_VERSION_GRCh37, GENOME_VERSION_GRCh38, GENOME_VERSION_LOOKUP
from seqr.models import Sample, Individual
from seqr.utils.elasticsearch.utils import InvalidSearchException
from seqr.utils.elasticsearch.constants import RECESSIVE, COMPOUND_HET, X_LINKED_RECESSIVE, ANY_AFFECTED, NEW_SV_FIELD, \
    INHERITANCE_FILTERS, ALT_ALT, REF_REF, REF_ALT, HAS_ALT, HAS_REF, SPLICE_AI_FIELD, MAX_NO_LOCATION_COMP_HET_FAMILIES, \
    CLINVAR_SIGNFICANCE_MAP, HGMD_CLASS_MAP, CLINVAR_PATH_SIGNIFICANCES, CLINVAR_KEY, HGMD_KEY, PATH_FREQ_OVERRIDE_CUTOFF, \
    SCREEN_KEY

logger = logging.getLogger(__name__)

AFFECTED = Individual.AFFECTED_STATUS_AFFECTED
UNAFFECTED = Individual.AFFECTED_STATUS_UNAFFECTED
VARIANT_DATASET = Sample.DATASET_TYPE_VARIANT_CALLS
SV_DATASET = Sample.DATASET_TYPE_SV_CALLS
MITO_DATASET = Sample.DATASET_TYPE_MITO_CALLS

STRUCTURAL_ANNOTATION_FIELD = 'structural'

VARIANT_KEY_FIELD = 'variantId'
GROUPED_VARIANTS_FIELD = 'variants'
GNOMAD_GENOMES_FIELD = 'gnomad_genomes'

COMP_HET_ALT = 'COMP_HET_ALT'
INHERITANCE_FILTERS = deepcopy(INHERITANCE_FILTERS)
INHERITANCE_FILTERS[COMPOUND_HET][AFFECTED] = COMP_HET_ALT

GCNV_KEY = f'{SV_DATASET}_{Sample.SAMPLE_TYPE_WES}'
SV_KEY = f'{SV_DATASET}_{Sample.SAMPLE_TYPE_WGS}'

CONSEQUENCE_RANKS = [
    "transcript_ablation",
    "splice_acceptor_variant",
    "splice_donor_variant",
    "stop_gained",
    "frameshift_variant",
    "stop_lost",
    "start_lost",  # new in v81
    "initiator_codon_variant",  # deprecated
    "transcript_amplification",
    "inframe_insertion",
    "inframe_deletion",
    "missense_variant",
    "protein_altering_variant",  # new in v79
    "splice_region_variant",
    "incomplete_terminal_codon_variant",
    "start_retained_variant",
    "stop_retained_variant",
    "synonymous_variant",
    "coding_sequence_variant",
    "mature_miRNA_variant",
    "5_prime_UTR_variant",
    "3_prime_UTR_variant",
    "non_coding_transcript_exon_variant",
    "non_coding_exon_variant",  # deprecated
    "intron_variant",
    "NMD_transcript_variant",
    "non_coding_transcript_variant",
    "nc_transcript_variant",  # deprecated
    "upstream_gene_variant",
    "downstream_gene_variant",
    "TFBS_ablation",
    "TFBS_amplification",
    "TF_binding_site_variant",
    "regulatory_region_ablation",
    "regulatory_region_amplification",
    "feature_elongation",
    "regulatory_region_variant",
    "feature_truncation",
    "intergenic_variant",
]
CONSEQUENCE_RANK_MAP = {c: i for i, c in enumerate(CONSEQUENCE_RANKS)}
SCREEN_CONSEQUENCES = ['CTCF-bound', 'CTCF-only', 'DNase-H3K4me3', 'PLS', 'dELS', 'pELS', 'DNase-only', 'low-DNase']
SCREEN_CONSEQUENCE_RANK_MAP = {c: i for i, c in enumerate(SCREEN_CONSEQUENCES)}

SV_CONSEQUENCE_RANKS = [
    'COPY_GAIN', 'LOF', 'DUP_LOF', 'DUP_PARTIAL', 'INTRONIC', 'INV_SPAN', 'NEAREST_TSS', 'PROMOTER', 'UTR',
]
SV_CONSEQUENCE_RANK_MAP = {c: i for i, c in enumerate(SV_CONSEQUENCE_RANKS)}
SV_TYPES = ['gCNV_DEL', 'gCNV_DUP', 'BND', 'CPX', 'CTX', 'DEL', 'DUP', 'INS', 'INV', 'CNV']
SV_TYPE_DISPLAYS = [t.replace('gCNV_', '') for t in SV_TYPES]
SV_TYPE_MAP = {c: i for i, c in enumerate(SV_TYPES)}
SV_TYPE_DETAILS = [
    'INS_iDEL', 'INVdel', 'INVdup', 'ME', 'ME:ALU', 'ME:LINE1', 'ME:SVA', 'dDUP', 'dDUP_iDEL', 'delINV', 'delINVdel',
    'delINVdup', 'dupINV', 'dupINVdel', 'dupINVdup',
]


CLINVAR_SIGNIFICANCES = [
    'Pathogenic', 'Pathogenic,_risk_factor', 'Pathogenic,_Affects', 'Pathogenic,_drug_response',
    'Pathogenic,_drug_response,_protective,_risk_factor', 'Pathogenic,_association', 'Pathogenic,_other',
    'Pathogenic,_association,_protective', 'Pathogenic,_protective', 'Pathogenic/Likely_pathogenic',
    'Pathogenic/Likely_pathogenic,_risk_factor', 'Pathogenic/Likely_pathogenic,_drug_response',
    'Pathogenic/Likely_pathogenic,_other', 'Likely_pathogenic,_risk_factor', 'Likely_pathogenic',
    'Conflicting_interpretations_of_pathogenicity', 'Conflicting_interpretations_of_pathogenicity,_risk_factor',
    'Conflicting_interpretations_of_pathogenicity,_Affects',
    'Conflicting_interpretations_of_pathogenicity,_association,_risk_factor',
    'Conflicting_interpretations_of_pathogenicity,_other,_risk_factor',
    'Conflicting_interpretations_of_pathogenicity,_association',
    'Conflicting_interpretations_of_pathogenicity,_drug_response',
    'Conflicting_interpretations_of_pathogenicity,_drug_response,_other',
    'Conflicting_interpretations_of_pathogenicity,_other', 'Uncertain_significance',
    'Uncertain_significance,_risk_factor', 'Uncertain_significance,_Affects', 'Uncertain_significance,_association',
    'Uncertain_significance,_other', 'Affects', 'Affects,_risk_factor', 'Affects,_association', 'other', 'NA',
    'risk_factor', 'drug_response,_risk_factor', 'association', 'confers_sensitivity', 'drug_response', 'not_provided',
    'Likely_benign,_drug_response,_other', 'Likely_benign,_other', 'Likely_benign', 'Benign/Likely_benign,_risk_factor',
    'Benign/Likely_benign,_drug_response', 'Benign/Likely_benign,_other', 'Benign/Likely_benign', 'Benign,_risk_factor',
    'Benign,_confers_sensitivity', 'Benign,_association,_confers_sensitivity', 'Benign,_drug_response', 'Benign,_other',
    'Benign,_protective', 'Benign', 'protective,_risk_factor', 'protective',
]
CLINVAR_SIG_MAP = {sig: i for i, sig in enumerate(CLINVAR_SIGNIFICANCES)}
HGMD_SIGNIFICANCES = ['DM', 'DM?', 'DP', 'DFP', 'FP', 'FTV', 'R']
HGMD_SIG_MAP = {sig: i for i, sig in enumerate(HGMD_SIGNIFICANCES)}

PREDICTION_FIELD_ID_LOOKUP = {
    'fathmm': ['D', 'T'],
    'mut_taster': ['D', 'A', 'N', 'P'],
    'polyphen': ['D', 'P', 'B'],
    'sift': ['D', 'T'],
    'mitotip': ['likely_pathogenic',  'possibly_pathogenic', 'possibly_benign', 'likely_benign'],
    'haplogroup_defining': ['Y'],
}


class BaseHailTableQuery(object):

    GENOTYPE_QUERY_MAP = {
        REF_REF: lambda gt: gt.is_hom_ref(),
        REF_ALT: lambda gt: gt.is_het(),
        COMP_HET_ALT: lambda gt: gt.is_het(),
        ALT_ALT: lambda gt: gt.is_hom_var(),
        HAS_ALT: lambda gt: gt.is_non_ref(),
        HAS_REF: lambda gt: gt.is_hom_ref() | gt.is_het_ref(),
    }

    GENOTYPE_FIELDS = {}
    GENOTYPE_RESPONSE_KEYS = {}
    POPULATIONS = {}
    PREDICTION_FIELDS_CONFIG = {}
    TRANSCRIPT_FIELDS = ['gene_id']
    ANNOTATION_OVERRIDE_FIELDS = []

    CORE_FIELDS = ['genotypes']
    BASE_ANNOTATION_FIELDS = {
        'familyGuids': lambda r: hl.array(r.familyGuids),
    }
    LIFTOVER_ANNOTATION_FIELDS = {
        'liftedOverGenomeVersion': lambda r: hl.if_else(  # In production - format all rg37_locus fields in main HT?
            hl.is_defined(r.rg37_locus), hl.literal(GENOME_VERSION_GRCh37), hl.missing(hl.dtype('str')),
        ),
        'liftedOverChrom': lambda r: hl.if_else(
            hl.is_defined(r.rg37_locus), r.rg37_locus.contig, hl.missing(hl.dtype('str')),
        ),
        'liftedOverPos': lambda r: hl.if_else(
            hl.is_defined(r.rg37_locus), r.rg37_locus.position, hl.missing(hl.dtype('int32')),
        ),
    }
    COMPUTED_ANNOTATION_FIELDS = {}

    @classmethod
    def populations_configs(cls):
        populations = {
            pop: {field.lower(): field for field in ['AF', 'AC', 'AN', 'Hom', 'Hemi', 'Het']}
            for pop in cls.POPULATIONS.keys()
        }
        for pop, pop_config in cls.POPULATIONS.items():
            populations[pop].update(pop_config)
        return populations

    @property
    def annotation_fields(self):
        annotation_fields = {
            'populations': lambda r: hl.struct(**{
                population: self.population_expression(r, population, pop_config)
                for population, pop_config in self.populations_configs().items()
            }),
            'predictions': lambda r: hl.struct(**{
                prediction: hl.array(PREDICTION_FIELD_ID_LOOKUP[prediction])[r[path[0]][path[1]]]
                if prediction in PREDICTION_FIELD_ID_LOOKUP else r[path[0]][path[1]]
                for prediction, path in self.PREDICTION_FIELDS_CONFIG.items()
            }),
            'transcripts': lambda r: hl.or_else(
                r.sortedTranscriptConsequences, hl.empty_array(r.sortedTranscriptConsequences.dtype.element_type)
            ).map(lambda t: hl.struct(
                majorConsequence=self.get_major_consequence(t),
                **{_to_camel_case(k): t[k] for k in self.TRANSCRIPT_FIELDS},
            )).group_by(lambda t: t.geneId),
        }
        annotation_fields.update(self.BASE_ANNOTATION_FIELDS)
        if self._genome_version == GENOME_VERSION_LOOKUP[GENOME_VERSION_GRCh38]:
            annotation_fields.update(self.LIFTOVER_ANNOTATION_FIELDS)
        return annotation_fields

    def population_expression(self, r, population, pop_config):
        return hl.struct(**{
            response_key: hl.or_else(r[population][field], '' if response_key == 'id' else 0)
            for response_key, field in pop_config.items() if field is not None
        })

    @staticmethod
    def get_major_consequence(transcript):
        raise NotImplementedError

    def __init__(self, data_source, samples, genome_version, gene_ids=None, **kwargs):
        self._genome_version = genome_version
        self._comp_het_ht = None
        self._filtered_genes = gene_ids
        self._allowed_consequences = None
        self._allowed_consequences_secondary = None

        self._load_filtered_table(data_source, samples, **kwargs)

    def _load_filtered_table(self, data_source, samples, intervals=None, inheritance_mode=None, pathogenicity=None,
                             annotations=None, annotations_secondary=None, **kwargs):
        consequence_overrides = {
            CLINVAR_KEY: set(), HGMD_KEY: set(), SCREEN_KEY: None, SPLICE_AI_FIELD: None,
            NEW_SV_FIELD: None, STRUCTURAL_ANNOTATION_FIELD: None,
        }
        self._parse_pathogenicity_overrides(pathogenicity, consequence_overrides)
        self._parse_annotations_overrides(annotations, annotations_secondary, consequence_overrides)

        self._ht = self.import_filtered_table(
            data_source, samples, intervals=self._parse_intervals(intervals), genome_version=self._genome_version,
            consequence_overrides=consequence_overrides, allowed_consequences=self._allowed_consequences,
            allowed_consequences_secondary=self._allowed_consequences_secondary, inheritance_mode=inheritance_mode, **kwargs,
        )
        if self._filtered_genes:
            self._ht = self._filter_gene_ids(self._ht, self._filtered_genes)

        if inheritance_mode in {RECESSIVE, COMPOUND_HET}:
            is_all_recessive_search = inheritance_mode == RECESSIVE
            self._filter_compound_hets(is_all_recessive_search)
            if is_all_recessive_search:
                self._ht = self._ht.transmute(familyGuids=self._ht.recessiveFamilies)
                self._ht = self._ht.filter(hl.is_defined(self._ht.familyGuids) & (self._ht.familyGuids.size() > 0))
                if self._allowed_consequences_secondary:
                    self._ht = self._ht.filter(self._ht.has_allowed_consequence | self._ht.override_consequences)
            else:
                self._ht = None

    @classmethod
    def import_filtered_table(cls, data_source, samples, intervals=None, inheritance_mode=None, quality_filter=None,
                              consequence_overrides=None, **kwargs):
        load_table_kwargs = {'_intervals': intervals, '_filter_intervals': bool(intervals)}

        quality_filter = quality_filter or {}
        vcf_quality_filter = quality_filter.get('vcf_filter')
        quality_filter = cls._format_quality_filter(quality_filter)
        clinvar_path_terms = cls._get_clinvar_path_terms(consequence_overrides)

        family_filter_kwargs = cls._get_family_table_filter_kwargs(
            load_table_kwargs=load_table_kwargs, clinvar_path_terms=clinvar_path_terms, **kwargs)

        family_samples = defaultdict(list)
        for s in samples:
            family_samples[s.individual.family].append(s)
        cls._validate_search_criteria(
            num_families=len(family_samples), has_location_search=bool(intervals), inheritance_mode=inheritance_mode,
            **kwargs)

        family_set_fields = {}
        family_dict_fields = {}
        if clinvar_path_terms and quality_filter:
            family_set_fields['passesQualityFamilies'] = 'passesQuality'
        if inheritance_mode in {RECESSIVE, COMPOUND_HET}:
            family_dict_fields['compHetFamilyCarriers'] = 'unaffectedCompHetCarriers'
            if inheritance_mode == RECESSIVE:
                family_set_fields['recessiveFamilies'] = 'isRecessiveFamily'

        families_ht = None
        logger.info(f'Loading data for {len(family_samples)} families ({cls.__name__})')
        for f, f_samples in family_samples.items():
            family_ht = hl.read_table(f'/hail_datasets/{data_source}_families/{f.guid}.ht', **load_table_kwargs)

            logger.info(f'Initial count for {f.guid}: {family_ht.count()}')
            family_ht = cls._filter_family_table(
                family_ht, family_samples=f_samples, quality_filter=quality_filter, clinvar_path_terms=clinvar_path_terms,
                inheritance_mode=inheritance_mode, consequence_overrides=consequence_overrides,
                **kwargs, **family_filter_kwargs)
            logger.info(f'Prefiltered {f.guid} to {family_ht.count()} rows')

            family_ht = family_ht.transmute(
                genotypes=family_ht.entries.map(lambda gt: gt.select(
                    'sampleId', 'individualGuid', familyGuid=f.guid,
                    numAlt=hl.if_else(hl.is_defined(gt.GT), gt.GT.n_alt_alleles(), -1),
                    **{cls.GENOTYPE_RESPONSE_KEYS.get(k, k): gt[field] for k, field in cls.GENOTYPE_FIELDS.items()}
                )))

            family_ht = family_ht.select_globals()
            if families_ht is not None:
                families_ht = families_ht.join(family_ht, how='outer')
                families_ht = families_ht.select(
                    genotypes=hl.bind(
                        lambda g1, g2: g1.extend(g2),
                        hl.or_else(families_ht.genotypes, hl.empty_array(families_ht.genotypes.dtype.element_type)),
                        hl.or_else(families_ht.genotypes_1, hl.empty_array(families_ht.genotypes.dtype.element_type)),
                    ),
                    **{k: hl.bind(
                        lambda family_set: hl.if_else(
                            hl.is_defined(families_ht[field]) & families_ht[field], family_set.add(f.guid), family_set),
                        hl.or_else(families_ht[k], hl.empty_set(hl.tstr)),
                    ) for k, field in family_set_fields.items()},
                    **{k: hl.bind(
                        lambda family_arr: hl.if_else(
                            hl.is_defined(families_ht[field]), family_arr.append((f.guid, families_ht[field])), family_arr,
                        ),
                        hl.or_else(families_ht[k], hl.empty_array(families_ht[k].dtype.element_type)),
                    ) for k, field in family_dict_fields.items()},
                )
            else:
                families_ht = family_ht.transmute(
                    **{k: hl.or_missing(family_ht[field], {f.guid}) for k, field in family_set_fields.items()},
                    **{k: hl.or_missing(hl.is_defined(family_ht[field]), [(f.guid, family_ht[field])])
                       for k, field in family_dict_fields.items()},
                )

        if families_ht is None:
            raise InvalidSearchException(
                'Inheritance based search is disabled in families with no data loaded for affected individuals')

        if family_dict_fields:
            families_ht = families_ht.annotate(**{k: hl.dict(families_ht[k]) for k in family_dict_fields.keys()})

        logger.info(f'Prefiltered to {families_ht.count()} rows ({cls.__name__})')

        # TODO - use query_table
        annotation_ht = hl.read_table(f'/hail_datasets/{data_source}.ht', **load_table_kwargs)
        ht = families_ht.annotate(**annotation_ht[families_ht.key])

        if clinvar_path_terms and quality_filter:
            ht = ht.annotate(genotypes=hl.if_else(
                cls._has_clivar_terms_expr(ht, clinvar_path_terms),
                ht.genotypes, ht.genotypes.filter(lambda x: ht.passesQualityFamilies.contains(x.familyGuid))
            )).drop('passesQualityFamilies')
            ht = ht.filter(ht.genotypes.size() > 0)

        ht = ht.annotate(
            familyGuids=ht.genotypes.group_by(lambda x: x.familyGuid).key_set(),
            genotypes=ht.genotypes.group_by(lambda x: x.individualGuid).map_values(lambda x: x[0]),
        )
        return cls._filter_annotated_table(
            ht, consequence_overrides=consequence_overrides, clinvar_path_terms=clinvar_path_terms,
            vcf_quality_filter=vcf_quality_filter, **kwargs)

    @classmethod
    def _validate_search_criteria(cls, inheritance_mode=None, allowed_consequences=None, **kwargs):
        if inheritance_mode in {RECESSIVE, COMPOUND_HET} and not allowed_consequences:
            raise InvalidSearchException('Annotations must be specified to search for compound heterozygous variants')

    @classmethod
    def _get_family_table_filter_kwargs(cls, **kwargs):
        return {}

    @classmethod
    def _filter_family_table(cls, family_ht, family_samples=None, inheritance_mode=None, inheritance_filter=None,
                             genome_version=None, quality_filter=None, clinvar_path_terms=None, **kwargs):
        family_ht = cls._filter_family_inheritance(
            family_samples, family_ht, inheritance_mode, inheritance_filter, genome_version)
        if family_ht is None:
            return None

        if quality_filter:
            quality_filter_expr = family_ht.entries.all(lambda gt: cls._genotype_passes_quality(gt, quality_filter))
            if clinvar_path_terms:
                family_ht = family_ht.annotate(passesQuality=quality_filter_expr)
            else:
                family_ht = family_ht.filter(quality_filter_expr)

        return family_ht

    @classmethod
    def _filter_family_inheritance(cls, family_samples, family_ht, inheritance_mode, inheritance_filter, genome_version):
        sample_index_id_map = dict(enumerate(hl.eval(family_ht.sample_ids)))
        sample_id_index_map = {v: k for k, v in sample_index_id_map.items()}
        sample_individual_map = {s.sample_id: s.individual.guid for s in family_samples}
        missing_samples = set(sample_individual_map.keys()) - set(sample_id_index_map.keys())
        if missing_samples:
            raise InvalidSearchException(
                f'The following samples are available in seqr but missing the loaded data: {", ".join(missing_samples)}'
            )
        sample_index_individual_map = {
            sample_id_index_map[sample_id]: i_guid for sample_id, i_guid in sample_individual_map.items()
        }

        family_ht = family_ht.annotate(entries=hl.enumerate(family_ht.entries).filter(
            lambda x: hl.set(set(sample_index_individual_map.keys())).contains(x[0])
        ).map(
            lambda x: hl.or_else(x[1], cls._missing_entry(x[1])).annotate(
                sampleId=hl.dict(sample_index_id_map)[x[0]],
                individualGuid=hl.dict(sample_index_individual_map)[x[0]],
            )))

        if not (inheritance_filter or inheritance_mode):
            return family_ht

        individual_affected_status = inheritance_filter.get('affected') or {}
        sample_affected_statuses = {
            s: individual_affected_status.get(s.individual.guid) or s.individual.affected
            for s in family_samples
        }
        affected_status_samples = {
            s.sample_id for s, status in sample_affected_statuses.items() if status == AFFECTED
        }
        if not affected_status_samples:
            return None

        if inheritance_mode == X_LINKED_RECESSIVE:
            x_chrom_interval = hl.parse_locus_interval(
                hl.get_reference(genome_version).x_contigs[0], reference_genome=genome_version)
            family_ht = family_ht.filter(cls.get_x_chrom_filter(family_ht, x_chrom_interval))

        if inheritance_mode == ANY_AFFECTED:
            genotype_filter = family_ht.entries.any(
                lambda x: hl.set(affected_status_samples).contains(x.sampleId) & cls.GENOTYPE_QUERY_MAP[HAS_ALT](x.GT)
            )
        else:
            inheritance_filter.update(INHERITANCE_FILTERS[inheritance_mode])
            genotype_filter = cls._get_sample_genotype_filter(
                family_ht, sample_id_index_map, sample_affected_statuses, inheritance_mode, inheritance_filter)

        if inheritance_mode in {RECESSIVE, COMPOUND_HET}:
            family_ht, genotype_filter = cls._filter_comp_hets(
                family_ht, genotype_filter, sample_id_index_map, inheritance_mode, inheritance_filter, sample_affected_statuses)

        return family_ht.filter(genotype_filter)

    @classmethod
    def _missing_entry(cls, entry):
        entry_type = dict(**entry.dtype)
        return hl.struct(**{k: hl.missing(v) for k, v in entry_type.items()})

    @classmethod
    def _filter_comp_hets(cls, family_ht, genotype_filter, sample_id_index_map, inheritance_mode, inheritance_filter, sample_affected_statuses):
        unaffected_samples = {
            s.sample_id for s, status in sample_affected_statuses.items() if status == UNAFFECTED
        }

        family_ht = family_ht.annotate(
            passesGtFilter=genotype_filter,
            unaffectedCompHetCarriers=hl.set(
                family_ht.entries.filter(
                    lambda x: hl.set(unaffected_samples).contains(x.sampleId) & ~cls.GENOTYPE_QUERY_MAP[REF_REF](x.GT)
                ).map(lambda x: x.sampleId)
            ),
        )
        genotype_filter = family_ht.passesGtFilter

        # remove variants where all unaffected individuals are het
        has_unaffected_ref_filter = None if len(unaffected_samples) < 2 else family_ht.entries.any(
            lambda x: hl.set(unaffected_samples).contains(x.sampleId) & cls.GENOTYPE_QUERY_MAP[REF_REF](x.GT)
        )

        if inheritance_mode == RECESSIVE:
            inheritance_filter.update(INHERITANCE_FILTERS[COMPOUND_HET])
            comp_het_gt_filter = cls._get_sample_genotype_filter(
                family_ht, sample_id_index_map, sample_affected_statuses, COMPOUND_HET, inheritance_filter)
            if has_unaffected_ref_filter is not None:
                comp_het_gt_filter &= has_unaffected_ref_filter
            family_ht = family_ht.annotate(
                isRecessiveFamily=family_ht.passesGtFilter,
                unaffectedCompHetCarriers=hl.or_missing(comp_het_gt_filter, family_ht.unaffectedCompHetCarriers),
            )
            genotype_filter = family_ht.isRecessiveFamily | hl.is_defined(family_ht.unaffectedCompHetCarriers)

        elif has_unaffected_ref_filter is not None:
            genotype_filter &= has_unaffected_ref_filter

        return family_ht, genotype_filter

    @classmethod
    def _get_sample_genotype_filter(cls, family_ht, sample_id_index_map, sample_affected_statuses, inheritance_mode, inheritance_filter):
        individual_genotype_filter = (inheritance_filter or {}).get('genotype') or {}
        genotype_filter_exprs = []
        for s, status in sample_affected_statuses.items():
            genotype = individual_genotype_filter.get(s.individual.guid) or inheritance_filter.get(status)
            if inheritance_mode == X_LINKED_RECESSIVE and status == UNAFFECTED and s.individual.sex == Individual.SEX_MALE:
                genotype = REF_REF
            if genotype:
                genotype_filter_exprs.append(
                    cls.GENOTYPE_QUERY_MAP[genotype](family_ht.entries[sample_id_index_map[s.sample_id]].GT)
                )

        genotype_filter = genotype_filter_exprs[0]
        for f in genotype_filter_exprs:
            genotype_filter &= f
        return genotype_filter

    @classmethod
    def _genotype_passes_quality(cls, gt, quality_filter):
        quality_filter_expr = None
        for field, value in quality_filter.items():
            field_filter = gt[field] >= value
            if quality_filter_expr is None:
                quality_filter_expr = field_filter
            else:
                quality_filter_expr &= field_filter
        return quality_filter_expr

    @classmethod
    def _filter_annotated_table(cls, ht, custom_query=None, frequencies=None, in_silico=None, clinvar_path_terms=None,
                                vcf_quality_filter=None, consequence_overrides=None,
                                allowed_consequences=None, allowed_consequences_secondary=None, **kwargs):
        if custom_query:
            # In production: should either remove the "custom search" functionality,
            # or should come up with a simple json -> hail query parsing here
            raise NotImplementedError

        ht = cls._filter_by_frequency(ht, frequencies, clinvar_path_terms)
        ht = cls._filter_by_in_silico(ht, in_silico)
        ht = cls._filter_by_annotations(ht, allowed_consequences, allowed_consequences_secondary, consequence_overrides)
        if vcf_quality_filter is not None:
            ht = cls._filter_vcf_filters(ht)

        return ht

    @staticmethod
    def _filter_gene_ids(ht, gene_ids):
        return ht.filter(ht.sortedTranscriptConsequences.any(lambda t: hl.set(gene_ids).contains(t.gene_id)))

    @staticmethod
    def _should_add_chr_prefix(genome_version):
        reference_genome = hl.get_reference(genome_version)
        return any(c.startswith('chr') for c in reference_genome.contigs)

    @staticmethod
    def _formatted_chr_interval(interval):
        return f'[chr{interval.replace("[", "")}' if interval.startswith('[') else f'chr{interval}'

    def _parse_intervals(self, intervals):
        if intervals:
            add_chr_prefix = self._should_add_chr_prefix(genome_version=self._genome_version)
            raw_intervals = intervals
            intervals = [hl.eval(hl.parse_locus_interval(
                self._formatted_chr_interval(interval) if add_chr_prefix else interval,
                reference_genome=self._genome_version, invalid_missing=True)
            ) for interval in intervals]
            invalid_intervals = [raw_intervals[i] for i, interval in enumerate(intervals) if interval is None]
            if invalid_intervals:
                raise InvalidSearchException(f'Invalid intervals: {", ".join(invalid_intervals)}')
        return intervals

    def _parse_annotations_overrides(self, annotations, annotations_secondary, consequence_overrides):
        annotations = {k: v for k, v in (annotations or {}).items() if v}
        annotation_override_fields = {k for k, v in consequence_overrides.items() if v is None}
        for field in annotation_override_fields:
            value = annotations.pop(field, None)
            if field in self.ANNOTATION_OVERRIDE_FIELDS:
                consequence_overrides[field] = value

        self._allowed_consequences = sorted({ann for anns in annotations.values() for ann in anns})
        if annotations_secondary:
            self._allowed_consequences_secondary = sorted(
                {ann for anns in annotations_secondary.values() for ann in anns})

    def _parse_pathogenicity_overrides(self, pathogenicity, consequence_overrides):
        for clinvar_filter in (pathogenicity or {}).get('clinvar', []):
            consequence_overrides[CLINVAR_KEY].update(CLINVAR_SIGNFICANCE_MAP.get(clinvar_filter, []))
        for hgmd_filter in (pathogenicity or {}).get('hgmd', []):
            consequence_overrides[HGMD_KEY].update(HGMD_CLASS_MAP.get(hgmd_filter, []))

    @classmethod
    def _filter_vcf_filters(cls, ht):
        return ht.filter(hl.is_missing(ht.filters) | (ht.filters.length() < 1))

    @classmethod
    def _filter_by_frequency(cls, ht, frequencies, clinvar_path_terms):
        frequencies = {k: v for k, v in (frequencies or {}).items() if k in cls.POPULATIONS}
        if not frequencies:
            return ht

        has_path_override = clinvar_path_terms and any(
            freqs.get('af') or 1 < PATH_FREQ_OVERRIDE_CUTOFF for freqs in frequencies.values())
        populations_configs = cls.populations_configs()

        for pop, freqs in sorted(frequencies.items()):
            pop_filter = None
            if freqs.get('af') is not None:
                af_field = populations_configs[pop].get('filter_af') or populations_configs[pop]['af']
                pop_filter = ht[pop][af_field] <= freqs['af']
                if has_path_override and freqs['af'] < PATH_FREQ_OVERRIDE_CUTOFF:
                    pop_filter |= (
                        cls._has_clivar_terms_expr(ht, clinvar_path_terms) &
                        (ht[pop][af_field] <= PATH_FREQ_OVERRIDE_CUTOFF)
                    )
            elif freqs.get('ac') is not None:
                ac_field = populations_configs[pop]['ac']
                if ac_field:
                    pop_filter = ht[pop][ac_field] <= freqs['ac']

            if freqs.get('hh') is not None:
                hom_field = populations_configs[pop]['hom']
                hemi_field = populations_configs[pop]['hemi']
                if hom_field:
                    hh_filter = ht[pop][hom_field] <= freqs['hh']
                    if pop_filter is None:
                        pop_filter = hh_filter
                    else:
                        pop_filter &= hh_filter
                if hemi_field:
                    hh_filter = ht[pop][hemi_field] <= freqs['hh']
                    if pop_filter is None:
                        pop_filter = hh_filter
                    else:
                        pop_filter &= hh_filter

            if pop_filter is not None:
                ht = ht.filter(hl.is_missing(ht[pop]) | pop_filter)

        return ht

    @classmethod
    def _filter_by_in_silico(cls, ht, in_silico_filters):
        in_silico_filters = {
            k: v for k, v in (in_silico_filters or {}).items()
            if k == 'requireScore' or (k in cls.PREDICTION_FIELDS_CONFIG and v is not None and len(v) != 0)
        }
        require_score = in_silico_filters.pop('requireScore', False)
        if not in_silico_filters:
            return ht

        in_silico_q = None
        missing_in_silico_q = None
        for in_silico, value in in_silico_filters.items():
            score_path = cls.PREDICTION_FIELDS_CONFIG[in_silico]
            ht_value = ht[score_path[0]][score_path[1]]
            if in_silico in PREDICTION_FIELD_ID_LOOKUP:
                score_filter = ht_value == PREDICTION_FIELD_ID_LOOKUP[in_silico].index(value)
            else:
                score_filter = ht_value >= float(value)

            if in_silico_q is None:
                in_silico_q = score_filter
            else:
                in_silico_q |= score_filter

            if not require_score:
                missing_score_filter = hl.is_missing(ht_value)
                if missing_in_silico_q is None:
                    missing_in_silico_q = missing_score_filter
                else:
                    missing_in_silico_q &= missing_score_filter

        if missing_in_silico_q is not None:
            in_silico_q |= missing_in_silico_q

        return ht.filter(in_silico_q)

    @classmethod
    def _filter_by_annotations(cls, ht, allowed_consequences, allowed_consequences_secondary, consequence_overrides):
        annotation_exprs = {}

        annotation_override_filter = cls._get_annotation_override_filter(ht, consequence_overrides)
        annotation_exprs['override_consequences'] = False if annotation_override_filter is None else annotation_override_filter

        if allowed_consequences:
            annotation_exprs['has_allowed_consequence'] = ht.sortedTranscriptConsequences.any(
                lambda tc: cls._is_allowed_consequence_filter(tc, allowed_consequences))

        if allowed_consequences_secondary:
            annotation_exprs['has_allowed_secondary_consequence'] = ht.sortedTranscriptConsequences.any(
                lambda tc: cls._is_allowed_consequence_filter(tc, allowed_consequences_secondary))

        ht = ht.annotate(**annotation_exprs)
        filter_fields = [k for k, v in annotation_exprs.items() if v is not False]

        if not filter_fields:
            return ht

        consequence_filter = ht[filter_fields[0]]
        for field in filter_fields[1:]:
            consequence_filter |= ht[field]
        return ht.filter(consequence_filter)

    @classmethod
    def _get_annotation_override_filter(cls, ht, consequence_overrides):
        annotation_filters = []

        if consequence_overrides[CLINVAR_KEY]:
            annotation_filters.append(hl.set({
                CLINVAR_SIG_MAP[s] for s in consequence_overrides[CLINVAR_KEY]
            }).contains(ht.clinvar.clinical_significance_id))
        if consequence_overrides[HGMD_KEY]:
            allowed_classes = hl.set({HGMD_SIG_MAP[s] for s in consequence_overrides[HGMD_KEY]})
            annotation_filters.append(allowed_classes.contains(ht.hgmd.class_id))
        if consequence_overrides[SCREEN_KEY]:
            allowed_consequences = hl.set({SCREEN_CONSEQUENCE_RANK_MAP[c] for c in consequence_overrides[SCREEN_KEY]})
            annotation_filters.append(allowed_consequences.intersection(hl.set(ht.screen.region_type_id)).size() > 0)
        if consequence_overrides[SPLICE_AI_FIELD]:
            splice_ai = float(consequence_overrides[SPLICE_AI_FIELD])
            score_path = cls.PREDICTION_FIELDS_CONFIG[SPLICE_AI_FIELD]
            annotation_filters.append(ht[score_path[0]][score_path[1]] >= splice_ai)
        if consequence_overrides[STRUCTURAL_ANNOTATION_FIELD]:
            allowed_sv_types = hl.set({SV_TYPE_MAP[t] for t in consequence_overrides[STRUCTURAL_ANNOTATION_FIELD]})
            annotation_filters.append(allowed_sv_types.contains(ht.svType_id))

        if not annotation_filters:
            return None
        annotation_filter = annotation_filters[0]
        for af in annotation_filters[1:]:
            annotation_filter |= af
        return annotation_filter

    @staticmethod
    def _get_clinvar_path_terms(consequence_overrides):
        return [
            CLINVAR_SIG_MAP[f] for f in consequence_overrides[CLINVAR_KEY] if f in CLINVAR_PATH_SIGNIFICANCES
        ]

    @staticmethod
    def _has_clivar_terms_expr(ht, clinvar_terms):
        return hl.set(clinvar_terms).contains(ht.clinvar.clinical_significance_id)

    @staticmethod
    def _is_allowed_consequence_filter(tc, allowed_consequences):
        allowed_consequence_ids = hl.set({
            SV_CONSEQUENCE_RANK_MAP[c] for c in allowed_consequences if SV_CONSEQUENCE_RANK_MAP.get(c)
        })
        return hl.set(allowed_consequence_ids).contains(tc.major_consequence_id)

    @classmethod
    def _format_quality_filter(cls, quality_filter):
        parsed_quality_filter = {}
        for filter_k, value in quality_filter.items():
            field = cls.GENOTYPE_FIELDS.get(filter_k.replace('min_', ''))
            if field and value:
                parsed_quality_filter[field] = value
        return parsed_quality_filter

    @staticmethod
    def get_x_chrom_filter(ht, x_interval):
        return x_interval.contains(ht.locus)

    def _filter_compound_hets(self, is_all_recessive_search):
        ch_ht = self._ht.annotate(gene_ids=hl.set(self._ht.sortedTranscriptConsequences.map(lambda t: t.gene_id)))

        if is_all_recessive_search:
            ch_ht = ch_ht.filter(hl.is_defined(ch_ht.compHetFamilyCarriers) & (ch_ht.compHetFamilyCarriers.size() > 0))
            ch_ht = ch_ht.annotate(familyGuids=ch_ht.compHetFamilyCarriers.key_set())

        # Get possible pairs of variants within the same gene
        ch_ht = ch_ht.explode(ch_ht.gene_ids)
        formatted_rows_expr = hl.agg.collect(ch_ht.row)
        if self._allowed_consequences_secondary:
            v1_expr = hl.agg.filter(
                (ch_ht.override_consequences | ch_ht.has_allowed_consequence), formatted_rows_expr,
            )
            v2_expr = hl.agg.filter(
                (ch_ht.override_consequences | ch_ht.has_allowed_secondary_consequence), formatted_rows_expr,
            )
        else:
            v1_expr = formatted_rows_expr
            v2_expr = formatted_rows_expr

        ch_ht = ch_ht.group_by('gene_ids').aggregate(v1=v1_expr, v2=v2_expr)
        ch_ht = ch_ht.explode(ch_ht.v1)
        ch_ht = ch_ht.explode(ch_ht.v2)
        ch_ht = ch_ht.filter(ch_ht.v1[VARIANT_KEY_FIELD] != ch_ht.v2[VARIANT_KEY_FIELD])

        # Filter variant pairs for family and genotype
        ch_ht = ch_ht.annotate(family_guids=self._valid_comp_het_families_expr(ch_ht))
        ch_ht = ch_ht.filter(ch_ht.family_guids.size() > 0)
        ch_ht = ch_ht.annotate(
            v1=self._format_results(ch_ht.v1).annotate(**{
                'familyGuids': hl.array(ch_ht.family_guids), VARIANT_KEY_FIELD: ch_ht.v1[VARIANT_KEY_FIELD]
            }),
            v2=self._format_results(ch_ht.v2).annotate(**{
                'familyGuids': hl.array(ch_ht.family_guids), VARIANT_KEY_FIELD: ch_ht.v2[VARIANT_KEY_FIELD]
            }),
        )

        # Format pairs as lists and de-duplicate
        ch_ht = ch_ht.select(**{GROUPED_VARIANTS_FIELD: hl.sorted([ch_ht.v1, ch_ht.v2])})  # TODO #2496: sort with self._sort
        ch_ht = ch_ht.key_by(
            **{VARIANT_KEY_FIELD: hl.str(':').join(ch_ht[GROUPED_VARIANTS_FIELD].map(lambda v: v[VARIANT_KEY_FIELD]))})

        self._comp_het_ht = ch_ht.distinct()

    def _valid_comp_het_families_expr(self, ch_ht):
        both_var_families = ch_ht.v1.compHetFamilyCarriers.key_set().intersection(ch_ht.v2.compHetFamilyCarriers.key_set())
        # filter variants that are non-ref for any unaffected individual in both variants
        return both_var_families.filter(
            lambda family_guid: ch_ht.v1.compHetFamilyCarriers[family_guid].intersection(
                ch_ht.v2.compHetFamilyCarriers[family_guid]).size() == 0)

    def _format_results(self, ht):
        # logger.info(ht.aggregate(hl.agg.collect(ht.sortedTranscriptConsequences)))  # TODO debug
        results = ht.annotate(
            genomeVersion=self._genome_version.replace('GRCh', ''),
            **{k: v(ht) for k, v in self.annotation_fields.items()},
        )
        logger.info(results.aggregate(hl.agg.collect(results.transcripts)))  # TODO debug
        results = results.annotate(
            **{k: v(self, results) for k, v in self.COMPUTED_ANNOTATION_FIELDS.items()},
        )
        logger.info(results.aggregate(hl.agg.collect(results.transcripts)))  # TODO debug
        return results.select(
            'genomeVersion', *self.CORE_FIELDS, *set(list(self.COMPUTED_ANNOTATION_FIELDS.keys()) + list(self.annotation_fields.keys())))

    def search(self, page, num_results, sort):
        if self._ht:
            ht = self._format_results(self._ht)
            if self._comp_het_ht:
                ht = ht.join(self._comp_het_ht, 'outer')
        else:
            ht = self._comp_het_ht

        if not ht:
            raise InvalidSearchException('Filters must be applied before search')

        total_results = ht.count()
        logger.info(f'Total hits: {total_results}')

        # TODO #2496: page, sort
        collected = ht.take(num_results)
        hail_results = [
            self._json_serialize(row.get(GROUPED_VARIANTS_FIELD) or row.drop(GROUPED_VARIANTS_FIELD)) for row in collected
        ]
        return hail_results, total_results

    # For production: should use custom json serializer
    @classmethod
    def _json_serialize(cls, result):
        if isinstance(result, list):
            return [cls._json_serialize(o) for o in result]

        if isinstance(result, hl.Struct) or isinstance(result, hl.utils.frozendict):
            result = dict(result)

        if isinstance(result, dict):
            return {k: cls._json_serialize(v) for k, v in result.items()}

        return result


class BaseVariantHailTableQuery(BaseHailTableQuery):

    GENOTYPE_FIELDS = {f.lower(): f for f in ['DP', 'GQ']}
    POPULATIONS = {
        'callset': {'hom': None, 'hemi': None, 'het': None},
    }
    PREDICTION_FIELDS_CONFIG = {
        'fathmm': ('dbnsfp', 'FATHMM_pred_id'),
        'mut_taster': ('dbnsfp', 'MutationTaster_pred_id'),
        'polyphen': ('dbnsfp', 'Polyphen2_HVAR_pred_id'),
        'revel': ('dbnsfp', 'REVEL_score'),
        'sift': ('dbnsfp', 'SIFT_pred_id'),
    }
    TRANSCRIPT_FIELDS = BaseHailTableQuery.TRANSCRIPT_FIELDS + [
        'amino_acids', 'biotype', 'canonical', 'codons', 'hgvsc', 'hgvsp', 'lof', 'lof_filter', 'lof_flags', 'lof_info',
        'transcript_id', 'transcript_rank',
    ]

    CORE_FIELDS = BaseHailTableQuery.CORE_FIELDS + ['rsid', 'xpos']
    BASE_ANNOTATION_FIELDS = {
        'chrom': lambda r: r.locus.contig.replace("^chr", ""),
        'pos': lambda r: r.locus.position,
        'ref': lambda r: r.alleles[0],
        'alt': lambda r: r.alleles[1],
        'clinvar': lambda r: r.clinvar.select(
            'alleleId', 'goldStars',
            clinicalSignificance=hl.array(CLINVAR_SIGNIFICANCES)[r.clinvar.clinical_significance_id],
        ),
        'genotypeFilters': lambda r: hl.str(' ,').join(r.filters),  # In production - format in main HT?
        'mainTranscriptId': lambda r: r.sortedTranscriptConsequences[0].transcript_id,
    }
    BASE_ANNOTATION_FIELDS.update(BaseHailTableQuery.BASE_ANNOTATION_FIELDS)

    def _selected_main_transcript_expr(self, results):
        if not (self._filtered_genes or self._allowed_consequences):
            return hl.missing(hl.dtype('str'))

        get_matching_transcripts = lambda allowed_values, get_field: results.sortedTranscriptConsequences.filter(
            lambda t: hl.set(allowed_values).contains(get_field(t))).map(lambda t: t.transcript_id)

        gene_transcripts = None
        if self._filtered_genes:
            gene_transcripts = get_matching_transcripts(self._filtered_genes, lambda t: t.gene_id)

        consequence_transcripts = None
        if self._allowed_consequences:
            consequence_transcripts = get_matching_transcripts(self._allowed_consequences, self.get_major_consequence)
            if self._allowed_consequences_secondary:
                consequence_transcripts = hl.if_else(
                    consequence_transcripts.size() > 0, consequence_transcripts,
                    get_matching_transcripts(self._allowed_consequences_secondary, self.get_major_consequence))

        if gene_transcripts is not None:
            if consequence_transcripts is None:
                matched_transcripts = gene_transcripts
            else:
                matched_transcripts = hl.bind(
                    lambda t: hl.if_else(t.size() > 0, t, gene_transcripts),
                    gene_transcripts.filter(lambda t: consequence_transcripts.contains(t)),
                )
        else:
            matched_transcripts = consequence_transcripts

        return hl.if_else(
            matched_transcripts.contains(results.sortedTranscriptConsequences[0].transcript_id),
            hl.missing(hl.dtype('str')), matched_transcripts[0],
        )
    COMPUTED_ANNOTATION_FIELDS = {
        'selectedMainTranscriptId': _selected_main_transcript_expr,
    }

    @classmethod
    def import_filtered_table(cls, data_source, samples, intervals=None, exclude_intervals=False, **kwargs):
        ht = super(BaseVariantHailTableQuery, cls).import_filtered_table(
            data_source, samples, intervals=None if exclude_intervals else intervals,
            excluded_intervals=intervals if exclude_intervals else None, **kwargs)
        ht = ht.key_by(VARIANT_KEY_FIELD)
        return ht

    @classmethod
    def _filter_family_table(cls, family_ht, excluded_intervals=None, variant_ids=None, genome_version=None, **kwargs):
        if excluded_intervals:
            family_ht = hl.filter_intervals(family_ht, excluded_intervals, keep=False)
        if variant_ids:
            if len(variant_ids) == 1:
                variant_id_q = family_ht.alleles == [variant_ids[0][2], variant_ids[0][3]]
            else:
                if cls._should_add_chr_prefix(genome_version):
                    variant_ids = [(f'chr{chr}', *v_id) for chr, *v_id in variant_ids]
                variant_id_qs = [
                    (family_ht.locus == hl.locus(chrom, pos, reference_genome=genome_version)) &
                    (family_ht.alleles == [ref, alt])
                    for chrom, pos, ref, alt in variant_ids
                ]
                variant_id_q = variant_id_qs[0]
                for q in variant_id_qs[1:]:
                    variant_id_q |= q
            family_ht = family_ht.filter(variant_id_q)

        return super(BaseVariantHailTableQuery, cls)._filter_family_table(family_ht, genome_version=genome_version, **kwargs)

    @classmethod
    def _filter_annotated_table(cls, ht, rs_ids=None, **kwargs):
        if rs_ids:
            ht = ht.filter(hl.set(rs_ids).contains(ht.rsid))
        return super(BaseVariantHailTableQuery, cls)._filter_annotated_table(ht, **kwargs)

    @staticmethod
    def get_major_consequence(transcript):
        return hl.array(CONSEQUENCE_RANKS)[transcript.sorted_consequence_ids[0]]

    @staticmethod
    def _is_allowed_consequence_filter(tc, allowed_consequences):
        allowed_consequence_ids = hl.set({
            CONSEQUENCE_RANK_MAP[c] for c in allowed_consequences if CONSEQUENCE_RANK_MAP.get(c)
        })
        return allowed_consequence_ids.intersection(hl.set(tc.sorted_consequence_ids)).size() > 0


class VariantHailTableQuery(BaseVariantHailTableQuery):

    GENOTYPE_FIELDS = {f.lower(): f for f in ['AB', 'AD', 'PL']}
    GENOTYPE_FIELDS.update(BaseVariantHailTableQuery.GENOTYPE_FIELDS)
    POPULATIONS = {
        'topmed': {'hemi': None, 'het': None},
        'exac': {
            'filter_af': 'AF_POPMAX', 'ac': 'AC_Adj', 'an': 'AN_Adj', 'hom': 'AC_Hom', 'hemi': 'AC_Hemi', 'het': None,
        },
        'gnomad_exomes': {'filter_af': 'AF_POPMAX_OR_GLOBAL', 'het': None},
        GNOMAD_GENOMES_FIELD: {'filter_af': 'AF_POPMAX_OR_GLOBAL', 'het': None},
    }
    POPULATIONS.update(BaseVariantHailTableQuery.POPULATIONS)
    PREDICTION_FIELDS_CONFIG = {
        'cadd': ('cadd', 'PHRED'),
        'eigen': ('eigen', 'Eigen_phred'),
        'gnomad_noncoding': ('gnomad_non_coding_constraint', 'z_score'),
        'mpc': ('mpc', 'MPC'),
        'primate_ai': ('primate_ai', 'score'),
        'splice_ai': ('splice_ai', 'delta_score'),
        'splice_ai_consequence': ('splice_ai', 'splice_consequence'),
    }
    PREDICTION_FIELDS_CONFIG.update(BaseVariantHailTableQuery.PREDICTION_FIELDS_CONFIG)
    ANNOTATION_OVERRIDE_FIELDS = [SPLICE_AI_FIELD, SCREEN_KEY]

    BASE_ANNOTATION_FIELDS = {
        'hgmd': lambda r: r.hgmd.select('accession', **{'class': hl.array(HGMD_SIGNIFICANCES)[r.hgmd.class_id]}),
        'originalAltAlleles': lambda r: r.originalAltAlleles.map(lambda a: a.split('-')[-1]), # In production - format in main HT
        'screenRegionType': lambda r: hl.or_missing(
            r.screen.region_type_id.size() > 0,
            hl.array(SCREEN_CONSEQUENCES)[r.screen.region_type_id[0]]),
    }
    BASE_ANNOTATION_FIELDS.update(BaseVariantHailTableQuery.BASE_ANNOTATION_FIELDS)

    @classmethod
    def _validate_search_criteria(cls, num_families=None, has_location_search=None, inheritance_mode=None, **kwargs):
        if inheritance_mode in {RECESSIVE, COMPOUND_HET} and num_families > MAX_NO_LOCATION_COMP_HET_FAMILIES and not has_location_search:
            raise InvalidSearchException('Location must be specified to search for compound heterozygous variants across many families')
        super(VariantHailTableQuery, cls)._validate_search_criteria(inheritance_mode=inheritance_mode, **kwargs)

    @classmethod
    def _get_family_table_filter_kwargs(cls, frequencies=None, load_table_kwargs=None, clinvar_path_terms=None, **kwargs):
        gnomad_genomes_filter = (frequencies or {}).get(GNOMAD_GENOMES_FIELD, {})
        af_cutoff = gnomad_genomes_filter.get('af')
        if af_cutoff is None and gnomad_genomes_filter.get('ac') is not None:
            af_cutoff = 0.01
        if af_cutoff is None:
            return {}
        if clinvar_path_terms:
            af_cutoff = max(af_cutoff, PATH_FREQ_OVERRIDE_CUTOFF)

        high_af_ht = hl.read_table('/hail_datasets/high_af_variants.ht', **(load_table_kwargs or {}))
        if af_cutoff > 0.01:
            high_af_ht = high_af_ht.filter(high_af_ht.is_gt_10_percent)
        return {'high_af_ht': high_af_ht}

    @classmethod
    def _filter_family_table(cls, family_ht, high_af_ht=None, **kwargs):
        if high_af_ht is not None:
            family_ht = family_ht.filter(hl.is_missing(high_af_ht[family_ht.key]))

        return super(VariantHailTableQuery, cls)._filter_family_table(family_ht, **kwargs)

    @classmethod
    def _genotype_passes_quality(cls, gt, quality_filter):
        no_ab_quality_filter = {k: v for k, v in quality_filter.items() if k != 'AB'}
        quality_filter_expr = super(VariantHailTableQuery, cls)._genotype_passes_quality(gt, no_ab_quality_filter)
        ab_value = quality_filter.get('AB')
        if ab_value:
            # AB only relevant for hets
            field_filter = (gt.AB >= ab_value / 100) | ~gt.GT.is_het()
            if quality_filter_expr is None:
                quality_filter_expr = field_filter
            else:
                quality_filter_expr &= field_filter

        return quality_filter_expr


class MitoHailTableQuery(BaseVariantHailTableQuery):

    GENOTYPE_FIELDS = {
        'hl': 'HL',
        'mitoCn': 'mito_cn',
        'contamination': 'contamination',
    }
    GENOTYPE_FIELDS.update(BaseVariantHailTableQuery.GENOTYPE_FIELDS)
    POPULATIONS = {
        pop: {'hom': None, 'hemi': None, 'het': None} for pop in [
            'callset_heteroplasmy', 'gnomad_mito', 'gnomad_mito_heteroplasmy', 'helix', 'helix_heteroplasmy'
        ]
    }
    for pop in ['gnomad_mito_heteroplasmy', 'helix_heteroplasmy']:
        POPULATIONS[pop].update({'max_hl': 'max_hl'})
    POPULATIONS.update(BaseVariantHailTableQuery.POPULATIONS)
    PREDICTION_FIELDS_CONFIG = {
        'apogee': ('mitimpact', 'score'),
        'hmtvar': ('hmtvar', 'score'),
        'mitotip': ('mitotip', 'trna_prediction_id'),
        'haplogroup_defining': ('haplogroup', 'is_defining'),
    }
    PREDICTION_FIELDS_CONFIG.update(BaseVariantHailTableQuery.PREDICTION_FIELDS_CONFIG)
    BASE_ANNOTATION_FIELDS = {
        'commonLowHeteroplasmy': lambda r: r.common_low_heteroplasmy,
        'highConstraintRegion': lambda r: r.high_constraint_region,
        'mitomapPathogenic': lambda r: r.mitomap.pathogenic,
    }
    BASE_ANNOTATION_FIELDS.update(BaseVariantHailTableQuery.BASE_ANNOTATION_FIELDS)

    @classmethod
    def _format_quality_filter(cls, quality_filter):
        return super(MitoHailTableQuery, cls)._format_quality_filter(
            {k: v / 100 if k == 'min_hl' else v for k, v in (quality_filter or {}).items()}
        )


def _no_genotype_override(genotypes, field):
    return genotypes.values().any(lambda g: (g.numAlt > 0) & hl.is_missing(g[field]))


def _get_genotype_override_field(genotypes, default, field, agg):
    return hl.if_else(
        _no_genotype_override(genotypes, field), default, agg(genotypes.values().map(lambda g: g[field]))
    )


class BaseSvHailTableQuery(BaseHailTableQuery):

    GENOTYPE_QUERY_MAP = deepcopy(BaseHailTableQuery.GENOTYPE_QUERY_MAP)
    GENOTYPE_QUERY_MAP[COMP_HET_ALT] = GENOTYPE_QUERY_MAP[HAS_ALT]

    GENOTYPE_FIELDS = {'cn': 'CN'}
    GENOTYPE_RESPONSE_KEYS = {'gq_sv': 'gq'}
    POPULATIONS = {
        'sv_callset': {'hemi': None},
    }
    PREDICTION_FIELDS_CONFIG = {
        'strvctvre': ('strvctvre', 'score'),
    }

    BASE_ANNOTATION_FIELDS = {
        'chrom': lambda r: r.interval.start.contig.replace('^chr', ''),
        'pos': lambda r: r.interval.start.position,
        'end': lambda r: r.interval.end.position,
        'rg37LocusEnd': lambda r: hl.struct(contig=r.rg37_locus_end.contig, position=r.rg37_locus_end.position),
        'svType': lambda r: hl.array(SV_TYPE_DISPLAYS)[r.svType_id],

    }
    BASE_ANNOTATION_FIELDS.update(BaseHailTableQuery.BASE_ANNOTATION_FIELDS)
    ANNOTATION_OVERRIDE_FIELDS = [STRUCTURAL_ANNOTATION_FIELD, NEW_SV_FIELD]

    @classmethod
    def import_filtered_table(cls, data_source, samples, intervals=None, exclude_intervals=False, **kwargs):
        ht = super(BaseSvHailTableQuery, cls).import_filtered_table(data_source, samples, **kwargs)
        if intervals:
            interval_filter = hl.array(intervals).all(lambda interval: not interval.overlaps(ht.interval)) \
                if exclude_intervals else hl.array(intervals).any(lambda interval: interval.overlaps(ht.interval))
            ht = ht.filter(interval_filter)
        return ht

    def _parse_pathogenicity_overrides(self, pathogenicity, consequence_overrides):
        pass

    @staticmethod
    def get_x_chrom_filter(ht, x_interval):
        return ht.interval.overlaps(x_interval)

    @staticmethod
    def get_major_consequence(transcript):
        return hl.array(SV_CONSEQUENCE_RANKS)[transcript.major_consequence_id]

    @classmethod
    def _filter_family_table(cls, family_ht, consequence_overrides=None, **kwargs):
        if consequence_overrides[NEW_SV_FIELD]:
            family_ht = family_ht.filter(family_ht.entries.any(lambda x: x.newCall))

        return super(BaseSvHailTableQuery, cls)._filter_family_table(family_ht, **kwargs)


class GcnvHailTableQuery(BaseSvHailTableQuery):

    GENOTYPE_FIELDS = {
        f: f for f in ['start', 'end', 'numExon', 'geneIds', 'defragged', 'prevCall', 'prevOverlap', 'newCall']
    }
    GENOTYPE_FIELDS.update({'qs': 'QS'})
    GENOTYPE_FIELDS.update(BaseSvHailTableQuery.GENOTYPE_FIELDS)

    BASE_ANNOTATION_FIELDS = deepcopy(BaseSvHailTableQuery.BASE_ANNOTATION_FIELDS)
    BASE_ANNOTATION_FIELDS.update({
        'pos': lambda r: _get_genotype_override_field(r.genotypes, r.interval.start.position, 'start', hl.min),
        'end': lambda r: _get_genotype_override_field(r.genotypes, r.interval.end.position, 'end', hl.max),
        'numExon': lambda r: _get_genotype_override_field(r.genotypes, r.num_exon, 'numExon', hl.max),
    })
    COMPUTED_ANNOTATION_FIELDS = {
        'transcripts': lambda self, r: hl.if_else(
            _no_genotype_override(r.genotypes, 'geneIds'), r.transcripts, hl.bind(
                lambda gene_ids: hl.dict(r.transcripts.items().filter(lambda t: gene_ids.contains(t[0]))),
                r.genotypes.values().flatmap(lambda g: g.geneIds)
            ),
        )
    }

    @classmethod
    def _missing_entry(cls, entry):
        #  gCNV data has no ref/ref calls so a missing entry indicates that call
        return super(GcnvHailTableQuery, cls)._missing_entry(entry).annotate(GT=hl.Call([0, 0]))

    @classmethod
    def _filter_vcf_filters(cls, ht):
        pass


class SvHailTableQuery(BaseSvHailTableQuery):

    GENOTYPE_FIELDS = {'gq_sv': 'GQ_SV'}
    GENOTYPE_FIELDS.update(BaseSvHailTableQuery.GENOTYPE_FIELDS)
    POPULATIONS = {
        'gnomad_svs': {'id': 'ID', 'ac': None, 'an': None, 'hom': None, 'hemi': None, 'het': None},
    }
    POPULATIONS.update(BaseSvHailTableQuery.POPULATIONS)

    CORE_FIELDS = BaseHailTableQuery.CORE_FIELDS + [
        'algorithms', 'bothsidesSupport', 'cpxIntervals', 'svSourceDetail', 'xpos',
    ]
    BASE_ANNOTATION_FIELDS = {
        'genotypeFilters': lambda r: hl.str(' ,').join(r.filters),  # In production - format in main HT?
        'svTypeDetail': lambda r: hl.array(SV_TYPE_DETAILS)[r.svTypeDetail_id],
    }
    BASE_ANNOTATION_FIELDS.update(BaseSvHailTableQuery.BASE_ANNOTATION_FIELDS)


QUERY_CLASS_MAP = {
    VARIANT_DATASET: VariantHailTableQuery,
    MITO_DATASET: MitoHailTableQuery,
    GCNV_KEY: GcnvHailTableQuery,
    SV_KEY: SvHailTableQuery,
}

DATA_TYPE_POPULATIONS_MAP = {data_type: set(cls.POPULATIONS.keys()) for data_type, cls in QUERY_CLASS_MAP.items()}


class MultiDataTypeHailTableQuery(object):

    DATA_TYPE_ANNOTATION_FIELDS = []

    def __init__(self, data_source, *args, **kwargs):
        # TODO clean up unused multi data type properties
        self._data_types = list(data_source.keys())
        self.POPULATIONS = {}
        self.PREDICTION_FIELDS_CONFIG = {}
        self.GENOTYPE_FIELDS = {}
        self.BASE_ANNOTATION_FIELDS = {}
        self.COMPUTED_ANNOTATION_FIELDS = {}
        self.CORE_FIELDS = set()
        self.ANNOTATION_OVERRIDE_FIELDS = []
        for cls in [QUERY_CLASS_MAP[data_type] for data_type in self._data_types]:
            self.POPULATIONS.update(cls.POPULATIONS)
            self.PREDICTION_FIELDS_CONFIG.update(cls.PREDICTION_FIELDS_CONFIG)
            self.GENOTYPE_FIELDS.update(cls.GENOTYPE_FIELDS)
            self.BASE_ANNOTATION_FIELDS.update(cls.BASE_ANNOTATION_FIELDS)
            self.COMPUTED_ANNOTATION_FIELDS.update(cls.COMPUTED_ANNOTATION_FIELDS)
            self.CORE_FIELDS.update(cls.CORE_FIELDS)
            self.ANNOTATION_OVERRIDE_FIELDS += cls.ANNOTATION_OVERRIDE_FIELDS
        self.BASE_ANNOTATION_FIELDS.update({
            k: self._annotation_for_data_type(k) for k in self.DATA_TYPE_ANNOTATION_FIELDS
        })
        self.CORE_FIELDS = list(self.CORE_FIELDS - set(self.BASE_ANNOTATION_FIELDS.keys()))

        super(MultiDataTypeHailTableQuery, self).__init__(data_source, *args, **kwargs)

    def _annotation_for_data_type(self, field):
        def field_annotation(r):
            case = hl.case()
            for cls_type in self._data_types:
                cls = QUERY_CLASS_MAP[cls_type]
                if field in cls.BASE_ANNOTATION_FIELDS:
                    case = case.when(r.dataType == cls_type, cls.BASE_ANNOTATION_FIELDS[field](r))
            return case.or_missing()
        return field_annotation

    def population_expression(self, r, population, pop_config):
        return hl.or_missing(
            hl.dict(DATA_TYPE_POPULATIONS_MAP)[r.dataType].contains(population),
            super(MultiDataTypeHailTableQuery, self).population_expression(r, population, pop_config),
        )

    @staticmethod
    def join_mts(mt1, mt2):
        # TODO fix joining for flat tables
        mt = hl.experimental.full_outer_join_mt(mt1, mt2)

        mt = mt.select_cols()

        left_e_fields = set(mt.left_entry.dtype)
        right_e_fields = set(mt.right_entry.dtype)
        mt = mt.select_entries(
            **{k: hl.or_else(mt.left_entry[k], mt.right_entry[k]) for k in left_e_fields.intersection(right_e_fields)},
            **{k: mt.left_entry[k] for k in left_e_fields.difference(right_e_fields)},
            **{k: mt.right_entry[k] for k in right_e_fields.difference(left_e_fields)},
        )

        left_r_fields = set(mt.left_row.dtype)
        right_r_fields = set(mt.right_row.dtype)
        left_transcripts_type = dict(**mt.left_row.sortedTranscriptConsequences.dtype.element_type)
        right_transcripts_type = dict(**mt.right_row.sortedTranscriptConsequences.dtype.element_type)
        row_expressions = {k: mt.left_row[k] for k in left_r_fields.difference(right_r_fields)}
        row_expressions.update({k: mt.right_row[k] for k in right_r_fields.difference(left_r_fields)})

        if left_transcripts_type != right_transcripts_type:
            left_r_fields.remove('sortedTranscriptConsequences')
            right_r_fields.remove('sortedTranscriptConsequences')
            struct_types = left_transcripts_type
            struct_types.update(right_transcripts_type)

            def format_transcript(t):
                return t.select(**{k: t.get(k, hl.missing(v)) for k, v in struct_types.items()})

            row_expressions['sortedTranscriptConsequences'] = hl.or_else(
                mt.left_row.sortedTranscriptConsequences.map(format_transcript),
                mt.right_row.sortedTranscriptConsequences.map(format_transcript))

        row_expressions.update({
            k: hl.or_else(mt.left_row[k], mt.right_row[k])
            for k in left_r_fields.intersection(right_r_fields) if k != VARIANT_KEY_FIELD
        })
        return mt.select_rows(**row_expressions)

    @classmethod
    def import_filtered_table(cls, data_source, samples, **kwargs):
        data_types = list(data_source.keys())
        data_type_0 = data_types[0]

        ht = QUERY_CLASS_MAP[data_type_0].import_filtered_table(data_source[data_type_0], samples[data_type_0], **kwargs)
        ht = ht.annotate(dataType=data_type_0)

        for data_type in data_types[1:]:
            data_type_cls = QUERY_CLASS_MAP[data_type]
            sub_ht = data_type_cls.import_filtered_table(data_source[data_type], samples[data_type], **kwargs)
            sub_ht = sub_ht.annotate(dataType=data_type)
            # TODO implement flat table join
            ht = MultiDataTypeHailTableQuery.join_mts(ht, sub_ht)

        return ht


class AllSvHailTableQuery(MultiDataTypeHailTableQuery, BaseSvHailTableQuery):

    DATA_TYPE_ANNOTATION_FIELDS = ['end', 'pos']

    def __init__(self, *args, **kwargs):
        super(AllSvHailTableQuery, self).__init__(*args, **kwargs)
        self.COMPUTED_ANNOTATION_FIELDS = {
            k: lambda _self, r: hl.or_else(v(_self, r), r[k])
            for k, v in self.COMPUTED_ANNOTATION_FIELDS.items()
        }


class AllVariantHailTableQuery(MultiDataTypeHailTableQuery, VariantHailTableQuery):

    @classmethod
    def _format_quality_filter(cls, quality_filter):
        parsed_quality_filter = VariantHailTableQuery._format_quality_filter(quality_filter)
        parsed_quality_filter.update(MitoHailTableQuery._format_quality_filter(quality_filter))
        return parsed_quality_filter


class AllDataTypeHailTableQuery(AllVariantHailTableQuery):

    GENOTYPE_QUERY_MAP = AllSvHailTableQuery.GENOTYPE_QUERY_MAP

    DATA_TYPE_ANNOTATION_FIELDS = ['chrom', 'pos', 'end']

    @staticmethod
    def get_x_chrom_filter(ht, x_interval):
        return hl.if_else(
            hl.is_defined(ht.svType_id),
            BaseSvHailTableQuery.get_x_chrom_filter(ht, x_interval),
            VariantHailTableQuery.get_x_chrom_filter(ht, x_interval),
        )

    @staticmethod
    def _is_allowed_consequence_filter(tc, allowed_consequences):
        return hl.if_else(
            hl.is_defined(tc.sorted_consequence_ids),
            BaseVariantHailTableQuery._is_allowed_consequence_filter(tc, allowed_consequences),
            BaseSvHailTableQuery._is_allowed_consequence_filter(tc, allowed_consequences),
        )

    @staticmethod
    def get_major_consequence(transcript):
        return hl.if_else(
            hl.is_defined(transcript.sorted_consequence_ids),
            BaseVariantHailTableQuery.get_major_consequence(transcript),
            BaseSvHailTableQuery.get_major_consequence(transcript),
        )

    def _valid_comp_het_families_expr(self, ch_ht):
        valid_families = super(AllDataTypeHailTableQuery, self)._valid_comp_het_families_expr(ch_ht)
        invalid_families = self._invalid_hom_alt_individual_families(ch_ht.v1, ch_ht.v2).union(
            self._invalid_hom_alt_individual_families(ch_ht.v2, ch_ht.v1)
        )
        return valid_families.difference(invalid_families)

    @staticmethod
    def _invalid_hom_alt_individual_families(v1, v2):
        # SNPs overlapped by trans deletions may be incorrectly called as hom alt, and should be
        # considered comp hets with said deletions. Any other hom alt variants are not valid comp hets
        return hl.if_else(
            hl.is_defined(v1.svType) | ((v2.svType == 'DEL') & (v2.pos <= v1.pos) & (v1.pos <= v2.end)),
            hl.empty_set(hl.tstr),
            hl.set(v1.genotypes.values().filter(lambda g: g.numAlt == 2).map(lambda g: g.familyGuid))
        )


