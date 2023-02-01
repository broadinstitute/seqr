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
SV_TYPES = ['gCNV_DEL', 'gCNV_DUP', 'BND', 'CPX', 'CTX', 'DEL', 'DUP', 'INS', 'INV']
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

    @property
    def populations_configs(self):
        populations = {
            pop: {field.lower(): field for field in ['AF', 'AC', 'AN', 'Hom', 'Hemi', 'Het']}
            for pop in self.POPULATIONS.keys()
        }
        for pop, pop_config in self.POPULATIONS.items():
            populations[pop].update(pop_config)
        return populations

    @property
    def annotation_fields(self):
        annotation_fields = {
            'populations': lambda r: hl.struct(**{
                population: self.population_expression(r, population, pop_config)
                for population, pop_config in self.populations_configs.items()
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

    def __init__(self, data_source, samples, genome_version, gene_ids=None, intervals=None, exclude_intervals=False,
                 inheritance_mode=None, inheritance_filter=None, frequencies=None, quality_filter=None,
                 pathogenicity=None, annotations=None, **kwargs):
        self._genome_version = genome_version
        self._affected_status_samples = defaultdict(set)
        self._comp_het_ht = None
        self._filtered_genes = gene_ids
        self._has_location_filter = bool(intervals)
        self._allowed_consequences = None
        self._allowed_consequences_secondary = None
        self._save_samples(samples)

        self._consequence_overrides = {
            CLINVAR_KEY: set(), HGMD_KEY: set(), SCREEN_KEY: None, SPLICE_AI_FIELD: None,
            NEW_SV_FIELD: None, STRUCTURAL_ANNOTATION_FIELD: None,
        }
        self._parse_pathogenicity_overrides(pathogenicity)
        self._parse_annotations_overrides(annotations)

        self._mt = self._load_table(
            data_source, samples, intervals=intervals, exclude_intervals=exclude_intervals, frequencies=frequencies,
            inheritance_mode=inheritance_mode, inheritance_filter=inheritance_filter, quality_filter=quality_filter,
        )

        self._filter_variants(  # TODO inheritance needed for filter variants?
            inheritance_mode=inheritance_mode, inheritance_filter=inheritance_filter, frequencies=frequencies,
            quality_filter=quality_filter, **kwargs)

    def _save_samples(self, samples):
        self._individuals_by_sample_id = {s.sample_id: s.individual for s in samples}

    def _load_table(self, data_source, samples, intervals=None, **kwargs):
        mt = self.import_filtered_mt(
            data_source, samples, intervals=self._parse_intervals(intervals), genome_version=self._genome_version,
            consequence_overrides=self._consequence_overrides, **kwargs,
        )
        if self._filtered_genes:
            mt = self._filter_gene_ids(mt, self._filtered_genes)
        return mt

    @classmethod
    def import_filtered_mt(cls, data_source, samples, intervals=None, quality_filter=None, consequence_overrides=None, **kwargs):
        load_table_kwargs = {'_intervals': intervals, '_filter_intervals': bool(intervals)}

        quality_filter = cls._format_quality_filter(quality_filter or {})
        clinvar_path_terms = cls._get_clinvar_path_terms(consequence_overrides)

        family_filter_kwargs = cls._get_family_table_filter_kwargs(
            load_table_kwargs=load_table_kwargs, clinvar_path_terms=clinvar_path_terms, **kwargs)

        family_samples = defaultdict(list)
        for s in samples:
            family_samples[s.individual.family].append(s)
        families_mt = None
        logger.info(f'Loading data for {len(family_samples)} families ({cls.__name__})')
        for f, f_samples in family_samples.items():
            family_ht = hl.read_table(f'/hail_datasets/{data_source}_families/{f.guid}.ht', **load_table_kwargs)
            family_ht = family_ht.repartition(1)  # TODO at loading time
            family_mt = cls._family_ht_to_mt(family_ht).annotate_entries(familyGuid=f.guid)

            # TODO should be done at loading time
            sample_fields = ['GT'] + list(quality_filter.keys())
            family_mt = family_mt.annotate_rows(genotypes=hl.sorted(
                hl.agg.collect(hl.struct(sampleId=family_mt.s, **{field: family_mt[field] for field in sample_fields})),
                lambda o: o.sampleId))

            logger.info(f'Initial count for {f.guid}: {family_mt.rows().count()}')
            family_mt = cls._filter_family_table(
                family_mt, family_samples=f_samples, quality_filter=quality_filter, clinvar_path_terms=clinvar_path_terms,
                **kwargs, **family_filter_kwargs)
            logger.info(f'Prefiltered {f.guid} to {family_mt.rows().count()} rows')

            sample_individual_map = hl.dict({s.sample_id: s.individual.guid for s in f_samples})
            family_mt = family_mt.annotate_rows(
                genotypes=family_mt.genotypes.map(lambda gt: gt.select(
                    # TODO sampleId should come from array index not annotation
                    'sampleId', individualGuid=sample_individual_map[gt.sampleId], familyGuid=f.guid,
                    numAlt=hl.if_else(hl.is_defined(gt.GT), gt.GT.n_alt_alleles(), -1),
                    **{cls.GENOTYPE_RESPONSE_KEYS.get(k, k): gt.get(field) for k, field in cls.GENOTYPE_FIELDS.items()}
                )).group_by(lambda x: x.individualGuid).map_values(lambda x: x[0]))

            if families_mt:
                # TODO does not include row data from second table
                families_mt = families_mt.union_cols(family_mt, row_join_type='outer')
            else:
                families_mt = family_mt

        if families_mt is None:
            raise InvalidSearchException(
                'Inheritance based search is disabled in families with no data loaded for affected individuals')

        logger.info(f'Prefiltered to {families_mt.rows().count()} rows ({cls.__name__})')

        # TODO - use query_table
        ht = hl.read_table(f'/hail_datasets/{data_source}.ht', **load_table_kwargs)
        mt = families_mt.annotate_rows(**ht[families_mt.row_key])

        if clinvar_path_terms and quality_filter:
            # TODO use genotypes not entries for passesQuality, filter genotypes
            mt = mt.filter_entries(mt.passesQuality | cls._has_clivar_terms_expr(mt, clinvar_path_terms))

        mt = mt.annotate_rows(familyGuids=mt.genotypes.group_by(lambda x: x.familyGuid).key_set())
        return mt

    @classmethod
    def _family_ht_to_mt(cls, family_ht):
        keys = list(family_ht.key.keys())
        return family_ht.to_matrix_table(row_key=keys[:-1], col_key=keys[-1:])

    @classmethod
    def _get_family_table_filter_kwargs(cls, **kwargs):
        return {}

    @classmethod
    def _filter_family_table(cls, family_mt, family_samples=None, inheritance_mode=None, inheritance_filter=None,
                             genome_version=None, quality_filter=None, clinvar_path_terms=None, **kwargs):
        if inheritance_filter or inheritance_mode:
            family_mt = cls._filter_family_inheritance(
                family_samples, family_mt, inheritance_mode, inheritance_filter, genome_version)
        if family_mt is None:
            return None

        if quality_filter:
            quality_filter_expr = family_mt.genotypes.all(lambda gt: cls._genotype_passes_quality(gt, quality_filter))
            if clinvar_path_terms:
                family_mt = family_mt.annotate_entries(passesQuality=quality_filter_expr)
            else:
                family_mt = family_mt.filter_rows(quality_filter_expr)

        return family_mt

    @classmethod
    def _filter_family_inheritance(cls, family_samples, family_mt, inheritance_mode, inheritance_filter, genome_version):
        # TODO should come from table global at load time
        sample_id_index_map = {sample_id: i for i, sample_id in enumerate(sorted([s.sample_id for s in family_samples]))}

        individual_affected_status = inheritance_filter.get('affected') or {}
        sample_affected_statuses = {
            s: individual_affected_status.get(s.individual.guid) or s.individual.affected
            for s in family_samples
        }
        affected_status_sample_indices = {
            sample_id_index_map[s.sample_id] for s, status in sample_affected_statuses.items() if status == AFFECTED
        }
        if not affected_status_sample_indices:
            return None

        if inheritance_mode == X_LINKED_RECESSIVE:
            x_chrom_interval = hl.parse_locus_interval(
                hl.get_reference(genome_version).x_contigs[0], reference_genome=genome_version)
            family_mt = family_mt.filter_rows(cls.get_x_chrom_filter(family_mt, x_chrom_interval))

        if inheritance_mode == ANY_AFFECTED:
            genotype_filter = cls._get_any_sample_has_gt(family_mt, affected_status_sample_indices, HAS_ALT)
        else:
            inheritance_filter.update(INHERITANCE_FILTERS[inheritance_mode])
            genotype_filter_exprs = cls._get_sample_genotype_filters(
                family_mt, sample_id_index_map, sample_affected_statuses, inheritance_mode, inheritance_filter)
            genotype_filter = genotype_filter_exprs[0]
            for f in genotype_filter_exprs:
                genotype_filter &= f

        if inheritance_mode == COMPOUND_HET:
            # TODO handle all recessive case including comp het
            # remove variants where all unaffected individuals are het
            unaffected_sample_indices = {
                sample_id_index_map[s.sample_id] for s, status in sample_affected_statuses.items() if status == UNAFFECTED
            }
            if len(unaffected_sample_indices) > 1:
                genotype_filter &= cls._get_any_sample_has_gt(family_mt, unaffected_sample_indices, REF_REF)

        family_mt = family_mt.filter_rows(genotype_filter)

        # TODO comp het
        # TODO SV override newCall - _get_matched_families_expr
        return family_mt

    @classmethod
    def _get_any_sample_has_gt(cls, mt, allowed_sample_indices, genotype):
        return hl.enumerate(mt.genotypes).any(
            lambda en: hl.set(allowed_sample_indices).contains(en[0]) & cls.GENOTYPE_QUERY_MAP[genotype](en[1].GT)
        )

    @classmethod
    def _get_sample_genotype_filters(cls, family_mt, sample_id_index_map, sample_affected_statuses, inheritance_mode, inheritance_filter):
        individual_genotype_filter = (inheritance_filter or {}).get('genotype') or {}
        genotype_filter_exprs = []
        for s, status in sample_affected_statuses.items():
            genotype = individual_genotype_filter.get(s.individual.guid) or inheritance_filter.get(status)
            if inheritance_mode == X_LINKED_RECESSIVE and status == UNAFFECTED and s.individual.sex == Individual.SEX_MALE:
                genotype = REF_REF
            if genotype:
                genotype_filter_exprs.append(
                    cls.GENOTYPE_QUERY_MAP[genotype](family_mt.genotypes[sample_id_index_map[s.sample_id]].GT)
                )

        return genotype_filter_exprs

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

    @staticmethod
    def _filter_gene_ids(mt, gene_ids):
        return mt.filter_rows(mt.sortedTranscriptConsequences.any(lambda t: hl.set(gene_ids).contains(t.gene_id)))

    def _should_add_chr_prefix(self):
        reference_genome = hl.get_reference(self._genome_version)
        return any(c.startswith('chr') for c in reference_genome.contigs)

    @staticmethod
    def _formatted_chr_interval(interval):
        return f'[chr{interval.replace("[", "")}' if interval.startswith('[') else f'chr{interval}'

    def _parse_intervals(self, intervals):
        if intervals:
            add_chr_prefix = self._should_add_chr_prefix()
            raw_intervals = intervals
            intervals = [hl.eval(hl.parse_locus_interval(
                self._formatted_chr_interval(interval) if add_chr_prefix else interval,
                reference_genome=self._genome_version, invalid_missing=True)
            ) for interval in intervals]
            invalid_intervals = [raw_intervals[i] for i, interval in enumerate(intervals) if interval is None]
            if invalid_intervals:
                raise InvalidSearchException(f'Invalid intervals: {", ".join(invalid_intervals)}')
        return intervals

    def _filter_variants(self, inheritance_mode=None, inheritance_filter=None, variant_ids=None,
                         annotations_secondary=None, quality_filter=None, rs_ids=None,
                         frequencies=None, in_silico=None, custom_query=None):

        # TODO move to familty table
        self._filter_by_variant_ids(variant_ids)

        if rs_ids:
            self._filter_rsids(rs_ids)

        self._filter_custom(custom_query)

        self._filter_by_frequency(frequencies)

        self._filter_by_in_silico(in_silico)

        quality_filter = quality_filter or {}
        if quality_filter.get('vcf_filter') is not None:
            self._filter_vcf_filters()

        if inheritance_mode in {RECESSIVE, COMPOUND_HET}:
            comp_het_only = inheritance_mode == COMPOUND_HET
            self._filter_compound_hets(
                inheritance_filter, annotations_secondary, quality_filter, keep_main_ht=not comp_het_only,
            )
            if comp_het_only:
                return

        self._filter_main_annotations()
        self._annotate_filtered_genotypes(inheritance_mode, inheritance_filter)

    def _parse_annotations_overrides(self, annotations):
        annotations = {k: v for k, v in (annotations or {}).items() if v}
        annotation_override_fields = {k for k, v in self._consequence_overrides.items() if v is None}
        for field in annotation_override_fields:
            value = annotations.pop(field, None)
            if field in self.ANNOTATION_OVERRIDE_FIELDS:
                self._consequence_overrides[field] = value

        self._allowed_consequences = sorted({ann for anns in annotations.values() for ann in anns})

    def _parse_pathogenicity_overrides(self, pathogenicity):
        for clinvar_filter in (pathogenicity or {}).get('clinvar', []):
            self._consequence_overrides[CLINVAR_KEY].update(CLINVAR_SIGNFICANCE_MAP.get(clinvar_filter, []))
        for hgmd_filter in (pathogenicity or {}).get('hgmd', []):
            self._consequence_overrides[HGMD_KEY].update(HGMD_CLASS_MAP.get(hgmd_filter, []))

    def _filter_rsids(self, rs_ids):
        self._mt = self._mt.filter_rows(hl.set(rs_ids).contains(self._mt.rsid))

    def _filter_vcf_filters(self):
        self._mt = self._mt.filter_rows(hl.is_missing(self._mt.filters) | (self._mt.filters.length() < 1))

    def _filter_main_annotations(self):
        self._mt = self._filter_by_annotations(self._allowed_consequences)

    def _filter_by_variant_ids(self, variant_ids):
        if not variant_ids:
            return
        elif len(variant_ids) == 1:
            self._mt = self._mt.filter_rows(self._mt.alleles == [variant_ids[0][2], variant_ids[0][3]])
        else:
            add_chr_prefix = self._should_add_chr_prefix()
            id_q = self._variant_id_q(*variant_ids[0], add_chr_prefix=add_chr_prefix)
            for variant_id in variant_ids[1:]:
                id_q |= self._variant_id_q(*variant_id, add_chr_prefix=add_chr_prefix)

    def _variant_id_q(self, chrom, pos, ref, alt, add_chr_prefix=False):
        locus = hl.locus(f'chr{chrom}' if add_chr_prefix else chrom, pos, reference_genome=self._genome_version)
        return (self._mt.locus == locus) & (self._mt.alleles == [ref, alt])

    def _filter_custom(self, custom_query):
        if custom_query:
            # In production: should either remove the "custom search" functionality,
            # or should come up with a simple json -> hail query parsing here
            raise NotImplementedError

    def _filter_by_frequency(self, frequencies):
        frequencies = {k: v for k, v in (frequencies or {}).items() if k in self.populations_configs}
        if not frequencies:
            return

        clinvar_path_terms = self._get_clinvar_path_terms(self._consequence_overrides)
        has_path_override = clinvar_path_terms and any(
            freqs.get('af') or 1 < PATH_FREQ_OVERRIDE_CUTOFF for freqs in frequencies.values())

        for pop, freqs in sorted(frequencies.items()):
            pop_filter = None
            if freqs.get('af') is not None:
                af_field = self.populations_configs[pop].get('filter_af') or self.populations_configs[pop]['af']
                pop_filter = self._mt[pop][af_field] <= freqs['af']
                if has_path_override and freqs['af'] < PATH_FREQ_OVERRIDE_CUTOFF:
                    pop_filter |= (
                        self._has_clivar_terms_expr(self._mt, clinvar_path_terms) &
                        (self._mt[pop][af_field] <= PATH_FREQ_OVERRIDE_CUTOFF)
                    )
            elif freqs.get('ac') is not None:
                ac_field = self.populations_configs[pop]['ac']
                if ac_field:
                    pop_filter = self._mt[pop][ac_field] <= freqs['ac']

            if freqs.get('hh') is not None:
                hom_field = self.populations_configs[pop]['hom']
                hemi_field = self.populations_configs[pop]['hemi']
                if hom_field:
                    hh_filter = self._mt[pop][hom_field] <= freqs['hh']
                    if pop_filter is None:
                        pop_filter = hh_filter
                    else:
                        pop_filter &= hh_filter
                if hemi_field:
                    hh_filter = self._mt[pop][hemi_field] <= freqs['hh']
                    if pop_filter is None:
                        pop_filter = hh_filter
                    else:
                        pop_filter &= hh_filter

            if pop_filter is not None:
                self._mt = self._mt.filter_rows(hl.is_missing(self._mt[pop]) | pop_filter)

    def _filter_by_in_silico(self, in_silico_filters):
        in_silico_filters = {
            k: v for k, v in (in_silico_filters or {}).items()
            if k == 'requireScore' or (k in self.PREDICTION_FIELDS_CONFIG and v is not None and len(v) != 0)
        }
        require_score = in_silico_filters.pop('requireScore', False)
        if not in_silico_filters:
            return

        in_silico_q = None
        missing_in_silico_q = None
        for in_silico, value in in_silico_filters.items():
            score_path = self.PREDICTION_FIELDS_CONFIG[in_silico]
            ht_value = self._mt[score_path[0]][score_path[1]]
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

        self._mt = self._mt.filter_rows(in_silico_q)

    def _filter_by_annotations(self, allowed_consequences):
        annotation_filters = self._get_annotation_override_filters(self._mt)
        if allowed_consequences:
            annotation_filters.append(self._mt.sortedTranscriptConsequences.any(
                lambda tc: self._is_allowed_consequence_filter(tc, allowed_consequences)))

        if not annotation_filters:
            return self._mt
        annotation_filter = annotation_filters[0]
        for af in annotation_filters[1:]:
            annotation_filter |= af

        return self._mt.filter_rows(annotation_filter)

    def _get_annotation_override_filters(self, mt, use_parsed_fields=False):
        annotation_filters = []

        if self._consequence_overrides[CLINVAR_KEY]:
            if use_parsed_fields:
                allowed_significances = hl.set(self._consequence_overrides[CLINVAR_KEY])
                clinvar_key = 'clinicalSignificance'
            else:
                allowed_significances = hl.set({CLINVAR_SIG_MAP[s] for s in self._consequence_overrides[CLINVAR_KEY]})
                clinvar_key = 'clinical_significance_id'
            annotation_filters.append(allowed_significances.contains(mt.clinvar[clinvar_key]))
        if self._consequence_overrides[HGMD_KEY]:
            allowed_classes = hl.set({HGMD_SIG_MAP[s] for s in self._consequence_overrides[HGMD_KEY]})
            annotation_filters.append(allowed_classes.contains(mt.hgmd.class_id))
        if self._consequence_overrides[SCREEN_KEY]:
            allowed_consequences = hl.set({SCREEN_CONSEQUENCE_RANK_MAP[c] for c in self._consequence_overrides[SCREEN_KEY]})
            annotation_filters.append(allowed_consequences.intersection(hl.set(mt.screen.region_type_id)).size() > 0)
        if self._consequence_overrides[SPLICE_AI_FIELD]:
            splice_ai = float(self._consequence_overrides[SPLICE_AI_FIELD])
            score_path = ('predictions', 'splice_ai') if use_parsed_fields else self.PREDICTION_FIELDS_CONFIG[SPLICE_AI_FIELD]
            annotation_filters.append(mt[score_path[0]][score_path[1]] >= splice_ai)
        if self._consequence_overrides[STRUCTURAL_ANNOTATION_FIELD]:
            allowed_sv_types = hl.set({SV_TYPE_MAP[t] for t in self._consequence_overrides[STRUCTURAL_ANNOTATION_FIELD]})
            annotation_filters.append(allowed_sv_types.contains(mt.svType_id))

        return annotation_filters

    @staticmethod
    def _get_clinvar_path_terms(consequence_overrides):
        return [
            CLINVAR_SIG_MAP[f] for f in consequence_overrides[CLINVAR_KEY] if f in CLINVAR_PATH_SIGNIFICANCES
        ]

    @staticmethod
    def _has_clivar_terms_expr(mt, clinvar_terms):
        return hl.set(clinvar_terms).contains(mt.clinvar.clinical_significance_id)

    @staticmethod
    def _is_allowed_consequence_filter(tc, allowed_consequences):
        allowed_consequence_ids = hl.set({
            SV_CONSEQUENCE_RANK_MAP[c] for c in allowed_consequences if SV_CONSEQUENCE_RANK_MAP.get(c)
        })
        return hl.set(allowed_consequence_ids).contains(tc.major_consequence_id)

    def _annotate_filtered_genotypes(self, *args):
        self._mt = self._filter_by_genotype(self._mt, *args)

    def _filter_by_genotype(self, mt, inheritance_mode, inheritance_filter, max_families=None):
        # TODO deprecate
        individual_affected_status = inheritance_filter.get('affected') or {}
        if (inheritance_filter or inheritance_mode) and not self._affected_status_samples:
            self._set_validated_affected_status(individual_affected_status, max_families)

    def _set_validated_affected_status(self, individual_affected_status, max_families):
        for sample_id, individual in self._individuals_by_sample_id.items():
            affected = individual_affected_status.get(individual.guid) or individual.affected
            self._affected_status_samples[affected].add(sample_id)

        affected_families = {
            self._individuals_by_sample_id[sample_id].family for sample_id in self._affected_status_samples[AFFECTED]
        }
        self._individuals_by_sample_id = {
            sample_id: i for sample_id, i in self._individuals_by_sample_id.items() if i.family in affected_families
        }
        if max_families and len(affected_families) > max_families[0]:
            raise InvalidSearchException(max_families[1])

    @classmethod
    def _format_quality_filter(cls, quality_filter):
        parsed_quality_filter = {}
        for filter_k, value in quality_filter.items():
            field = cls.GENOTYPE_FIELDS.get(filter_k.replace('min_', ''))
            if field:
                parsed_quality_filter[field] = value
        return parsed_quality_filter

    @staticmethod
    def get_x_chrom_filter(mt, x_interval):
        return x_interval.contains(mt.locus)

    def _get_searchable_samples(self, mt):
        return hl.set(set(self._individuals_by_sample_id.keys()))

    def _filter_compound_hets(self, inheritance_filter, annotations_secondary, quality_filter, keep_main_ht=True):
        if not self._allowed_consequences:
            raise InvalidSearchException('Annotations must be specified to search for compound heterozygous variants')

        # Filter and format variants
        comp_het_consequences = set(self._allowed_consequences)
        if annotations_secondary:
            self._allowed_consequences_secondary = sorted(
                {ann for anns in annotations_secondary.values() for ann in anns})
            comp_het_consequences.update(self._allowed_consequences_secondary)

        ch_mt = self._filter_by_annotations(comp_het_consequences)
        ch_mt = self._filter_by_genotype(
            ch_mt, COMPOUND_HET, inheritance_filter, #quality_filter,
            max_families=None if self._has_location_filter else (MAX_NO_LOCATION_COMP_HET_FAMILIES, 'Location must be specified to search for compound heterozygous variants across many families')
        )
        ch_ht = self._format_results(ch_mt)

        # Get possible pairs of variants within the same gene
        ch_ht = ch_ht.annotate(gene_ids=ch_ht.transcripts.key_set())
        ch_ht = ch_ht.explode(ch_ht.gene_ids)
        ch_ht = ch_ht.group_by('gene_ids').aggregate(v1=hl.agg.collect(ch_ht.row).map(lambda v: v.drop('gene_ids')))
        # TODO of prefilter one of these to stricter annotation criteria, can remove _filter_valid_comp_het_annotation_pairs
        ch_ht = ch_ht.annotate(v2=ch_ht.v1)
        ch_ht = ch_ht.explode(ch_ht.v1)
        ch_ht = ch_ht.explode(ch_ht.v2)
        ch_ht = ch_ht.filter(ch_ht.v1[VARIANT_KEY_FIELD] != ch_ht.v2[VARIANT_KEY_FIELD])

        # Filter variant pairs for primary/secondary consequences
        if self._allowed_consequences and self._allowed_consequences_secondary:
            ch_ht = self._filter_valid_comp_het_annotation_pairs(ch_ht)

        # Filter variant pairs for family and genotype
        ch_ht = ch_ht.annotate(family_guids=hl.set(ch_ht.v1.familyGuids).intersection(hl.set(ch_ht.v2.familyGuids)))
        ch_ht = ch_ht.annotate(family_guids=self._valid_comp_het_families_expr(ch_ht))
        ch_ht = ch_ht.filter(ch_ht.family_guids.size() > 0)
        ch_ht = ch_ht.transmute(
            v1=ch_ht.v1.annotate(familyGuids=hl.array(ch_ht.family_guids)),
            v2=ch_ht.v2.annotate(familyGuids=hl.array(ch_ht.family_guids)),
        )

        # Format pairs as lists and de-duplicate
        ch_ht = ch_ht.annotate(
            **{GROUPED_VARIANTS_FIELD: hl.sorted([ch_ht.v1, ch_ht.v2])})  # TODO #2496: sort with self._sort
        ch_ht = ch_ht.annotate(
            **{VARIANT_KEY_FIELD: hl.str(':').join(ch_ht[GROUPED_VARIANTS_FIELD].map(lambda v: v[VARIANT_KEY_FIELD]))})
        ch_ht = ch_ht.select(GROUPED_VARIANTS_FIELD)

        self._comp_het_ht = ch_ht.distinct()

        if not keep_main_ht:
            self._mt = None

    @staticmethod
    def _non_alt_genotype(genotypes, i_guid):
        return ~genotypes.contains(i_guid) | (genotypes[i_guid].numAlt < 1)

    def _filter_valid_comp_het_annotation_pairs(self, ch_ht):
        primary_cs = hl.literal(set(self._allowed_consequences))
        secondary_cs = hl.literal(set(self._allowed_consequences_secondary))
        ch_ht = ch_ht.annotate(
            v1_csqs=ch_ht.v1.transcripts.values().flatmap(lambda x: x).map(lambda t: t.majorConsequence),
            v2_csqs=ch_ht.v2.transcripts.values().flatmap(lambda x: x).map(lambda t: t.majorConsequence)
        )
        has_annotation_filter = (ch_ht.v1_csqs.any(
            lambda c: primary_cs.contains(c)) & ch_ht.v2_csqs.any(
            lambda c: secondary_cs.contains(c))) | (ch_ht.v1_csqs.any(
            lambda c: secondary_cs.contains(c)) & ch_ht.v2_csqs.any(
            lambda c: primary_cs.contains(c)))

        for af in self._get_annotation_override_filters(ch_ht.v1, use_parsed_fields=True):
            has_annotation_filter |= af
        for af in self._get_annotation_override_filters(ch_ht.v2, use_parsed_fields=True):
            has_annotation_filter |= af

        return ch_ht.filter(has_annotation_filter)

    def _valid_comp_het_families_expr(self, ch_ht):
        unaffected_family_individuals = defaultdict(set)
        for sample_id in self._affected_status_samples[UNAFFECTED]:
            individual = self._individuals_by_sample_id[sample_id]
            unaffected_family_individuals[individual.family.guid].add(individual.guid)
        unaffected_family_individuals = hl.dict(unaffected_family_individuals)

        return ch_ht.family_guids.filter(lambda family_guid: unaffected_family_individuals[family_guid].all(
            lambda i_guid: self._non_alt_genotype(ch_ht.v1.genotypes, i_guid) | self._non_alt_genotype(ch_ht.v2.genotypes, i_guid)
        ))

    def _format_results(self, mt):
        results = mt.rows()
        results = results.annotate(
            genomeVersion=self._genome_version.replace('GRCh', ''),
            **{k: v(results) for k, v in self.annotation_fields.items()},
        )
        results = results.annotate(
            **{k: v(self, results) for k, v in self.COMPUTED_ANNOTATION_FIELDS.items()},
        )
        return results.select(
            'genomeVersion', *self.CORE_FIELDS, *set(list(self.COMPUTED_ANNOTATION_FIELDS.keys()) + list(self.annotation_fields.keys())))

    def search(self, page, num_results, sort):
        if self._mt:
            ht = self._format_results(self._mt)
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
    def import_filtered_mt(cls, data_source, samples, intervals=None, exclude_intervals=False, **kwargs):
        mt = super(BaseVariantHailTableQuery, cls).import_filtered_mt(
            data_source, samples, intervals=None if exclude_intervals else intervals,
            excluded_intervals=intervals if exclude_intervals else None, **kwargs)
        mt = mt.key_rows_by(VARIANT_KEY_FIELD)
        return mt

    @classmethod
    def _filter_family_table(cls, family_mt, excluded_intervals=None, **kwargs):
        if excluded_intervals:
            family_mt = hl.filter_intervals(family_mt, excluded_intervals, keep=False)
        return super(BaseVariantHailTableQuery, cls)._filter_family_table(family_mt, **kwargs)

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
    def _filter_family_table(cls, family_mt, high_af_ht=None, **kwargs):
        if high_af_ht is not None:
            family_mt = family_mt.filter_rows(hl.is_missing(high_af_ht[family_mt.row_key]))

        return super(VariantHailTableQuery, cls)._filter_family_table(family_mt, **kwargs)

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
    def import_filtered_mt(cls, data_source, samples, intervals=None, exclude_intervals=False, **kwargs):
        mt = super(BaseSvHailTableQuery, cls).import_filtered_mt(data_source, samples, **kwargs)
        if intervals:
            interval_filter = hl.array(intervals).all(lambda interval: not interval.overlaps(mt.interval)) \
                if exclude_intervals else hl.array(intervals).any(lambda interval: interval.overlaps(mt.interval))
            mt = mt.filter_rows(interval_filter)
        return mt

    def _parse_pathogenicity_overrides(self, pathogenicity):
        pass

    @staticmethod
    def get_x_chrom_filter(mt, x_interval):
        return mt.interval.overlaps(x_interval)

    @staticmethod
    def get_major_consequence(transcript):
        return hl.array(SV_CONSEQUENCE_RANKS)[transcript.major_consequence_id]

    def _get_matched_families_expr(self, mt, quality_filter, **kwargs):
        # TODO update family table prefilter
        inheritance_override_q = None
        if self._consequence_overrides[NEW_SV_FIELD]:
            inheritance_override_q = mt.newCall
        return super(BaseSvHailTableQuery, self)._get_matched_families_expr(
            mt, quality_filter,
            inheritance_override_q=inheritance_override_q,
        )


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
    def _family_ht_to_mt(cls, family_ht):
        mt = super(GcnvHailTableQuery, cls)._family_ht_to_mt(family_ht)
        #  gCNV data has no ref/ref calls so add them back in
        mt = mt.unfilter_entries()
        return mt.annotate_entries(GT=hl.or_else(mt.GT, hl.Call([0, 0])))

    def _filter_vcf_filters(self):
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

    def _save_samples(self, samples):
        self._individuals_by_sample_id = {}
        for data_type_samples in samples.values():
            for s in data_type_samples:
                self._individuals_by_sample_id[s.sample_id] = s.individual

        self._sample_ids_by_dataset_type = {k: {s.sample_id for s in v} for k, v in samples.items()}
        sample_sets = list(self._sample_ids_by_dataset_type.values())
        if all(sample_set == sample_sets[0] for sample_set in sample_sets[1:]):
            self._sample_ids_by_dataset_type = None

    def _get_searchable_samples(self, mt):
        if self._sample_ids_by_dataset_type:
            return hl.dict(self._sample_ids_by_dataset_type)[mt.dataType]
        return super(MultiDataTypeHailTableQuery, self)._get_searchable_samples(mt)

    @staticmethod
    def join_mts(mt1, mt2):
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
    def import_filtered_mt(cls, data_source, samples, **kwargs):
        data_types = list(data_source.keys())
        data_type_0 = data_types[0]

        mt = QUERY_CLASS_MAP[data_type_0].import_filtered_mt(data_source[data_type_0], samples[data_type_0], **kwargs)
        mt = mt.annotate_rows(dataType=data_type_0)

        for data_type in data_types[1:]:
            data_type_cls = QUERY_CLASS_MAP[data_type]
            sub_mt = data_type_cls.import_filtered_mt(data_source[data_type], samples[data_type], **kwargs)
            sub_mt = sub_mt.annotate_rows(dataType=data_type)
            mt = MultiDataTypeHailTableQuery.join_mts(mt, sub_mt)

        return mt


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
    def get_x_chrom_filter(mt, x_interval):
        return hl.if_else(
            hl.is_defined(mt.svType_id),
            BaseSvHailTableQuery.get_x_chrom_filter(mt, x_interval),
            VariantHailTableQuery.get_x_chrom_filter(mt, x_interval),
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

        individual_family_map = hl.dict({i.guid: i.family.guid for i in self._individuals_by_sample_id.values()})
        invalid_families = self._invalid_hom_alt_individuals(ch_ht.v1, ch_ht.v2).union(
            self._invalid_hom_alt_individuals(ch_ht.v2, ch_ht.v1)
        ).map(lambda i: individual_family_map[i])
        return valid_families.difference(invalid_families)

    @staticmethod
    def _invalid_hom_alt_individuals(v1, v2):
        # SNPs overlapped by trans deletions may be incorrectly called as hom alt, and should be
        # considered comp hets with said deletions. Any other hom alt variants are not valid comp hets
        return hl.if_else(
            hl.is_defined(v1.svType) | ((v2.svType == 'DEL') & (v2.pos <= v1.pos) & (v1.pos <= v2.end)),
            hl.empty_set(hl.tstr),
            v1.genotypes.key_set().filter(lambda i: v1.genotypes[i].numAlt == 2)
        )


