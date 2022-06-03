from collections import defaultdict
import hail as hl
import logging

from seqr.views.utils.json_utils import _to_camel_case
from reference_data.models import GENOME_VERSION_GRCh37
from seqr.models import Sample, Individual
from seqr.utils.elasticsearch.utils import InvalidSearchException
from seqr.utils.elasticsearch.constants import RECESSIVE, COMPOUND_HET, X_LINKED_RECESSIVE, ANY_AFFECTED, \
    INHERITANCE_FILTERS, ALT_ALT, REF_REF, REF_ALT, HAS_ALT, HAS_REF, SPLICE_AI_FIELD, MAX_NO_LOCATION_COMP_HET_FAMILIES, \
    CLINVAR_SIGNFICANCE_MAP, HGMD_CLASS_MAP, CLINVAR_PATH_SIGNIFICANCES, CLINVAR_KEY, HGMD_KEY, PATH_FREQ_OVERRIDE_CUTOFF

logger = logging.getLogger(__name__)

# For production: constants should have their own file

GENOTYPE_QUERY_MAP = {
    REF_REF: lambda gt: gt.is_hom_ref(),
    REF_ALT: lambda gt: gt.is_het(),
    ALT_ALT: lambda gt: gt.is_hom_var(),
    HAS_ALT: lambda gt: gt.is_non_ref(),
    HAS_REF: lambda gt: gt.is_hom_ref() | gt.is_het_ref(),
}

POPULATION_SUB_FIELDS = {
    'AF',
    'AC',
    'AN',
    'Hom',
    'Hemi',
    'Het',
}
POPULATIONS = {
    'topmed': {'hemi': None,'het': None},
    'g1k': {'filter_af': 'POPMAX_AF', 'hom': None, 'hemi': None, 'het': None},
    'exac': {
        'filter_af': 'AF_POPMAX', 'ac': 'AC_Adj', 'an': 'AN_Adj', 'hom': 'AC_Hom', 'hemi': 'AC_Hemi', 'het': None,
    },
    'gnomad_exomes': {'filter_AF':  'AF_POPMAX_OR_GLOBAL', 'het': None},
    'gnomad_genomes': {'filter_af': 'AF_POPMAX_OR_GLOBAL', 'het': None},
}
for pop_config in POPULATIONS.values():
    pop_config.update({field.lower(): field for field in POPULATION_SUB_FIELDS if field.lower() not in pop_config})

PREDICTION_FIELDS_CONFIG = {}
for path, pred_config in {
    'cadd': {'PHRED': 'cadd'},
    'dbnsfp': {
        'FATHMM_pred': 'fathmm',
        'GERP_RS': 'gerp_rs',
        'MetaSVM_pred': 'metasvm',
        'MutationTaster_pred': 'mutationtaster',
        'phastCons100way_vertebrate': 'phastcons_100_vert',
        'Polyphen2_HVAR_pred': 'polyphen',
        'REVEL_score': 'revel',
        'SIFT_pred': 'sift',
    },
    'eigen': {'Eigen_phred': 'eigen'},
    'mpc': {'MPC': 'mpc'},
    'primate_ai': {'score': 'primate_ai'},
    'splice_ai': {'delta_score': 'splice_ai', 'splice_consequence': 'splice_ai_consequence'},
}.items():
    PREDICTION_FIELDS_CONFIG.update({prediction: (path, sub_path) for sub_path, prediction in pred_config.items()})

GENOTYPE_QUALITY_FIELDS = ['AB', 'AD', 'DP', 'PL', 'GQ']
TRANSCRIPT_FIELDS = [
    'amino_acids', 'biotype', 'canonical', 'codons', 'gene_id', 'hgvsc', 'hgvsp',
    'lof', 'lof_flags', 'lof_filter', 'lof_info', 'major_consequence', 'transcript_id', 'transcript_rank',
]

CORE_FIELDS = ['hgmd', 'rsid', 'xpos', 'genotypes']
ANNOTATION_FIELDS = {
    'chrom': lambda r: r.locus.contig.replace("^chr", ""),
    'pos': lambda r: r.locus.position,
    'ref': lambda r: r.alleles[0],
    'alt': lambda r: r.alleles[1],
    'clinvar': lambda r: hl.struct( # In production - format in main HT?
        clinicalSignificance=r.clinvar.clinical_significance,
        alleleId=r.clinvar.allele_id,
        goldStars=r.clinvar.gold_stars,
    ),
    'familyGuids': lambda r: hl.array(r.familyGuids),
    'genotypeFilters': lambda r: hl.str(' ,').join(r.filters),  # In production - format in main HT?
    'liftedOverGenomeVersion': lambda r: hl.if_else(  # In production - format all rg37_locus fields in main HT?
        hl.is_defined(r.rg37_locus), hl.literal(GENOME_VERSION_GRCh37), hl.missing(hl.dtype('str')),
    ),
    'liftedOverChrom': lambda r: hl.if_else(
        hl.is_defined(r.rg37_locus), r.rg37_locus.contig, hl.missing(hl.dtype('str')),
    ),
    'liftedOverPos': lambda r: hl.if_else(
        hl.is_defined(r.rg37_locus), r.rg37_locus.position, hl.missing(hl.dtype('int32')),
    ),
    'mainTranscriptId': lambda r: r.sortedTranscriptConsequences[0].transcript_id,
    'originalAltAlleles': lambda r: r.originalAltAlleles.map(lambda a: a.split('-')[-1]), # In production - format in main HT
    'populations': lambda r: hl.struct(callset=hl.struct(af=r.AF, ac=r.AC, an=r.AN), **{
        population: hl.struct(**{
            response_key: hl.or_else(r[population][field], 0) for response_key, field in pop_config.items()
            if field is not None
        }) for population, pop_config in POPULATIONS.items()}
    ),
    'predictions': lambda r: hl.struct(**{
        prediction: r[path[0]][path[1]] for prediction, path in PREDICTION_FIELDS_CONFIG.items()
    }),
    'transcripts': lambda r: r.sortedTranscriptConsequences.map(
        lambda t: hl.struct(**{_to_camel_case(k): t[k] for k in TRANSCRIPT_FIELDS})).group_by(lambda t: t.geneId),
}

VARIANT_KEY_FIELD = 'variantId'
GROUPED_VARIANTS_FIELD = 'variants'


class BaseHailTableQuery(object):

    def __init__(self, data_source, samples, genome_version, **kwargs):
        self._genome_version = genome_version
        self._samples_by_id = {s.sample_id: s for s in samples}
        self._sample_ids_by_family = defaultdict(set)
        self._affected_status_samples = defaultdict(set)
        self._family_individual_affected_status = defaultdict(dict)
        self._comp_het_ht = None
        self._allowed_consequences = None
        self._allowed_consequences_secondary = None
        self._consequence_overrides = {CLINVAR_KEY: set(), HGMD_KEY: set(), SPLICE_AI_FIELD: None}

        self._mt = self._load_table(data_source, **kwargs)

    def _load_table(self, data_source, intervals=None, **kwargs):
        load_table_kwargs = {'_intervals': self._parse_intervals(intervals), '_filter_intervals': bool(intervals)}
        ht = hl.read_table(f'/hail_datasets/{data_source}.ht', **load_table_kwargs)
        sample_hts = {
            sample_id: hl.read_table(f'/hail_datasets/{data_source}_samples/{sample_id}.ht', **load_table_kwargs)
            for sample_id in self._samples_by_id.keys()
        }
        ht = ht.annotate(**{sample_id: s_ht[ht.locus, ht.alleles] for sample_id, s_ht in sample_hts.items()})
        return ht.to_matrix_table_row_major(sample_hts.keys(), col_field_name='s')

    def _parse_intervals(self, intervals):
        if intervals:
            intervals = [hl.eval(hl.parse_locus_interval(interval, reference_genome=self._genome_version))
                         for interval in intervals]
        return intervals

    @staticmethod
    def _sample_table(sample):
        # In production: should use a different model field, not elasticsearch_index
        return hl.read_table(f'/hail_datasets/{sample.elasticsearch_index}_samples/{sample.sample_id}.ht')

    def filter_variants(self, rs_ids=None, frequencies=None, pathogenicity=None, in_silico=None,
                        annotations=None, quality_filter=None, custom_query=None):
        for clinvar_filter in (pathogenicity or {}).get('clinvar', []):
            self._consequence_overrides[CLINVAR_KEY].update(CLINVAR_SIGNFICANCE_MAP.get(clinvar_filter, []))
        for hgmd_filter in (pathogenicity or {}).get('hgmd', []):
            self._consequence_overrides[HGMD_KEY].update(HGMD_CLASS_MAP.get(hgmd_filter, []))
        annotations = {k: v for k, v in (annotations or {}).items() if v}
        # TODO #2663: new_svs = bool(annotations.pop(NEW_SV_FIELD, False))
        self._consequence_overrides[SPLICE_AI_FIELD] = annotations.pop(SPLICE_AI_FIELD, None)
        self._allowed_consequences = sorted({ann for anns in annotations.values() for ann in anns})

        if rs_ids:
            self._filter_rsids(rs_ids)

        self._filter_custom(custom_query)

        self._filter_by_frequency(frequencies)

        self._filter_by_in_silico(in_silico)

        if quality_filter.get('vcf_filter') is not None:
            self._filter_vcf_filters()

    def _filter_rsids(self, rs_ids):
        self._mt = self._mt.filter_rows(hl.set(rs_ids).contains(self._mt.rsid))

    def _filter_vcf_filters(self):
        self._mt = self._mt.filter_rows(self._mt.filters.length() < 1)

    def filter_main_annotations(self):
        self._mt = self._filter_by_annotations(self._allowed_consequences)

    def filter_by_variant_ids(self, variant_ids):
        if len(variant_ids) == 1:
            self._mt = self._mt.filter_rows(self._mt.alleles == [variant_ids[0][2], variant_ids[0][3]])
        else:
            id_q = self._variant_id_q(*variant_ids[0])
            for variant_id in variant_ids[1:]:
                id_q |= self._variant_id_q(*variant_id)

    def _variant_id_q(self, chrom, pos, ref, alt):
        # TODO #2716: format chromosome for genome build
        return (self._mt.locus == hl.locus(f'chr{chrom}', pos, reference_genome=self._genome_version)) & (
                    self._mt.alleles == [ref, alt])

    def _filter_custom(self, custom_query):
        if custom_query:
            # In production: should either remove the "custom search" functionality,
            # or should come up with a simple json -> hail query parsing here
            raise NotImplementedError

    def _filter_by_frequency(self, frequencies):
        if not frequencies:
            return

        #  UI bug causes sv freq filter to be added despite no SV data
        frequencies.pop('sv_callset', None)

        clinvar_path_terms = [f for f in self._consequence_overrides[CLINVAR_KEY] if f in CLINVAR_PATH_SIGNIFICANCES]
        has_path_override = bool(clinvar_path_terms) and any(
            freqs.get('af') or 1 < PATH_FREQ_OVERRIDE_CUTOFF for freqs in frequencies.values())

        # In production: will not have callset frequency, may rename these fields
        callset_filter = frequencies.pop('callset', {}) or {}
        if callset_filter.get('af') is not None:
            callset_f = self._mt.AF <= callset_filter['af']
            if has_path_override and callset_filter['af'] < PATH_FREQ_OVERRIDE_CUTOFF:
                callset_f |= (
                        self._get_clinvar_filter(clinvar_path_terms) &
                        (self._mt.AF <= PATH_FREQ_OVERRIDE_CUTOFF)
                )
            self._mt = self._mt.filter_rows(callset_f)
        elif callset_filter.get('ac') is not None:
            self._mt = self._mt.filter_rows(self._mt.AC <= callset_filter['ac'])

        for pop, freqs in sorted(frequencies.items()):
            pop_filter = None
            if freqs.get('af') is not None:
                af_field = POPULATIONS[pop].get('filter_af') or POPULATIONS[pop]['af']
                pop_filter = self._mt[pop][af_field] <= freqs['af']
                if has_path_override and freqs['af'] < PATH_FREQ_OVERRIDE_CUTOFF:
                    pop_filter |= (
                            self._get_clinvar_filter(clinvar_path_terms) &
                            (self._mt[pop][af_field] <= PATH_FREQ_OVERRIDE_CUTOFF)
                    )
            elif freqs.get('ac') is not None:
                ac_field = POPULATIONS[pop]['ac']
                if ac_field:
                    pop_filter = self._mt[pop][ac_field] <= freqs['ac']

            if freqs.get('hh') is not None:
                hom_field = POPULATIONS[pop]['hom']
                hemi_field = POPULATIONS[pop]['hemi']
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
        in_silico_filters = {k: v for k, v in (in_silico_filters or {}).items() if v is not None and len(v) != 0}
        if not in_silico_filters:
            return

        in_silico_q = None
        missing_in_silico_q = None
        for in_silico, value in in_silico_filters.items():
            ht_value = self._get_in_silico_ht_field(in_silico)
            try:
                score_filter = ht_value >= float(value)
            except ValueError:
                score_filter = ht_value.startswith(value)

            if in_silico_q is None:
                in_silico_q = score_filter
            else:
                in_silico_q |= score_filter

            missing_score_filter = hl.is_missing(ht_value)
            if missing_in_silico_q is None:
                missing_in_silico_q = missing_score_filter
            else:
                missing_in_silico_q &= missing_score_filter

        self._mt = self._mt.filter_rows(in_silico_q | missing_in_silico_q)

    def _get_in_silico_ht_field(self, in_silico):
        score_path = PREDICTION_FIELDS_CONFIG[in_silico]
        return self._mt[score_path[0]][score_path[1]]

    def _filter_by_annotations(self, allowed_consequences):
        annotation_filters = []

        if self._consequence_overrides[CLINVAR_KEY]:
            annotation_filters.append(self._get_clinvar_filter(self._consequence_overrides[CLINVAR_KEY]))
        if self._consequence_overrides[HGMD_KEY]:
            allowed_classes = hl.set(self._consequence_overrides[HGMD_KEY])
            annotation_filters.append(allowed_classes.contains(self._mt.hgmd['class']))
        if self._consequence_overrides[SPLICE_AI_FIELD]:
            annotation_filters.append(
                self._get_in_silico_ht_field(SPLICE_AI_FIELD) >= float(self._consequence_overrides[SPLICE_AI_FIELD]))

        if allowed_consequences:
            annotation_filters.append(self._get_filtered_transcript_consequences(allowed_consequences))

        if not annotation_filters:
            return self._mt
        annotation_filter = annotation_filters[0]
        for af in annotation_filters[1:]:
            annotation_filter |= af

        return self._mt.filter_rows(annotation_filter)

    def _get_filtered_transcript_consequences(self, allowed_consequences):
        allowed_consequences_set = hl.set(allowed_consequences)
        consequence_terms = self._mt.sortedTranscriptConsequences.flatmap(lambda tc: tc.consequence_terms)
        return consequence_terms.any(lambda ct: allowed_consequences_set.contains(ct))

    def _get_clinvar_filter(self, clinvar_terms):
        allowed_significances = hl.set(clinvar_terms)
        return allowed_significances.contains(self._mt.clinvar.clinical_significance)

    def annotate_filtered_genotypes(self, *args):
        self._mt = self._filter_by_genotype(self._mt, *args)

    def _filter_by_genotype(self, mt, inheritance_mode, inheritance_filter, quality_filter, max_families=None):
        if inheritance_mode == ANY_AFFECTED:
            inheritance_filter = None
        elif inheritance_mode:
            inheritance_filter.update(INHERITANCE_FILTERS[inheritance_mode])

        if (inheritance_filter or inheritance_mode) and not self._affected_status_samples:
            individual_affected_status = inheritance_filter.get('affected') or {}
            for sample_id, sample in self._samples_by_id.items():
                indiv = sample.individual
                family_guid = indiv.family.guid
                self._sample_ids_by_family[family_guid].add(sample_id)
                affected = individual_affected_status.get(indiv.guid) or indiv.affected
                self._affected_status_samples[affected].add(sample_id)
                self._family_individual_affected_status[family_guid][indiv.guid] = affected # TODO remove

            no_search_families = {
                family_guid for family_guid, affected_status in self._family_individual_affected_status.items()
                if Individual.AFFECTED_STATUS_AFFECTED not in affected_status.values()
            }
            removed_samples = set()
            for family in no_search_families:
                removed_samples.update(self._sample_ids_by_family[family])
                del self._sample_ids_by_family[family]
            self._samples_by_id = {
                sample_id: s for sample_id, s in self._samples_by_id.items() if sample_id in removed_samples
            }

            if len(self._sample_ids_by_family) < 1:
                raise InvalidSearchException(
                    'Inheritance based search is disabled in families with no data loaded for affected individuals')
            if max_families and len(self._sample_ids_by_family) > max_families[0]:
                raise InvalidSearchException(max_families[1])

        sample_individual_map = hl.dict({sample_id: s.individual.guid for sample_id, s in self._samples_by_id.items()})
        sample_family_map = hl.dict({sample_id: s.individual.family.guid for sample_id, s in self._samples_by_id.items()})

        if inheritance_mode == ANY_AFFECTED:
            affected_samples = self._affected_status_samples[Individual.AFFECTED_STATUS_AFFECTED]
            if not affected_samples:
                raise InvalidSearchException('Any Affected search specified with no affected indiviudals')
            mt = mt.annotate_rows(familyGuids=hl.agg.filter(
                mt.GT.is_non_ref() & hl.set(affected_samples).contains(mt.s),
                hl.agg.collect_as_set(sample_family_map[mt.s])))
        elif not inheritance_filter:
            mt = mt.annotate_rows(familyGuids=hl.agg.filter(mt.GT.is_non_ref(), hl.agg.collect_as_set(sample_family_map[mt.s])))
        else:
            family_samples_map = hl.dict(self._sample_ids_by_family)
            # TODO actually construct query
            sample_q = hl.agg.filter((mt.GT.is_het() & hl.set(unaffected_samples).contains(mt.s)) | (
                        mt.GT.is_hom_var() & hl.set(affected_samples).contains(mt.s)), hl.agg.collect_as_set(mt.s))
            mt = mt.annotate_rows(familyGuids=hl.bind(
                lambda samples: family_samples_map.key_set().filter(lambda f: family_samples_map[f].is_subset(samples)),
                sample_q)
            )
            if inheritance_mode == COMPOUND_HET:
                multi_unaffected_fam_samples = {} # TODO
                multi_unaffected_samples = {} # TODO
                # remove variants where all unaffected individuals are het
                mt = mt.annotate_rows(notPhasedFamilies=hl.bind(
                    lambda samples: multi_unaffected_fam_samples.key_set().filter(
                        lambda f: multi_unaffected_fam_samples[f].is_subset(samples)),
                    hl.agg.filter(mt.GT.is_het() & hl.set(multi_unaffected_samples).contains(mt.s)))
                )
                mt = mt.transmute_rows(familyGuids=mt.familyGuids.difference(mt.notPhasedFamilies))

        # TODO actually apply qualty filters
        # family_hts = [
        #     self._get_filtered_family_table(
        #         samples = list(samples_by_family[family_guid].values()),
        #         affected_status = family_individual_affected_status.get(family_guid),
        #         inheritance_mode = inheritance_mode, inheritance_filter = inheritance_filter, quality_filter = quality_filter,
        # for family_guid in family_guids]

        mt = mt.filter_rows(mt.familyGuids.size() > 0)
        mt = mt.annotate_rows(genotypes=hl.agg.filter(
            mt.familyGuids.contains(sample_family_map[mt.s]),
            hl.agg.collect(hl.struct(
                individualGuid=sample_individual_map[mt.s],
                sampleId=mt.s,
                numAlt=mt.GT.n_alt_alleles(),
                **{f.lower(): mt[f] for f in GENOTYPE_QUALITY_FIELDS}
            ))).group_by(lambda x: x.individualGuid))

        return mt

    def _get_filtered_family_table(self, samples, affected_status, inheritance_mode, inheritance_filter,
                                   quality_filter, family_filter=None):
        sample_tables = [self._sample_table(sample) for sample in samples]

        individual_genotype_filter = (inheritance_filter or {}).get('genotype') or {}

        family_ht = None
        for i, sample_ht in enumerate(sample_tables):
            if quality_filter.get('min_gq'):
                sample_ht = sample_ht.filter(sample_ht.GQ > quality_filter['min_gq'])
            if quality_filter.get('min_ab'):
                #  AB only relevant for hets
                sample_ht = sample_ht.filter(~sample_ht.GT.is_het() | (sample_ht.AB > (quality_filter['min_ab'] / 100)))

            if inheritance_filter:
                individual = samples[i].individual
                affected = affected_status[individual.guid]
                genotype = individual_genotype_filter.get(individual.guid) or inheritance_filter.get(affected)
                sample_ht = self._sample_inheritance_ht(sample_ht, inheritance_mode, individual, affected, genotype)

            if family_ht is None:
                family_ht = sample_ht
            else:
                family_ht = family_ht.join(sample_ht)

        family_rename = {'GT': 'GT_0'}
        family_rename.update({f: f'{f}_0' for f in GENOTYPE_QUALITY_FIELDS})
        family_ht = family_ht.rename(family_rename)

        if family_filter is not None:
            family_filter_q = family_filter(family_ht, samples, affected_status)
            if family_filter_q is not None:
                family_ht = family_ht.filter(family_filter_q)

        return family_ht.annotate(
            genotypes=hl.array([hl.struct(
                individualGuid=hl.literal(sample.individual.guid),
                sampleId=hl.literal(sample.sample_id),
                numAlt=family_ht[f'GT_{i}'].n_alt_alleles(),
                **{f.lower(): family_ht[f'{f}_{i}'] for f in GENOTYPE_QUALITY_FIELDS}
            ) for i, sample in enumerate(samples)])).select('genotypes')

    def _sample_inheritance_ht(self, sample_ht, inheritance_mode, individual, affected, genotype):
        gt_filter = GENOTYPE_QUERY_MAP[genotype](sample_ht.GT)

        x_sample_ht = None
        if inheritance_mode in {X_LINKED_RECESSIVE, RECESSIVE}:
            x_sample_ht = hl.filter_intervals(
                # TODO #2716: format chromosome for genome build
                sample_ht, [hl.parse_locus_interval('chrX', reference_genome=self._genome_version)])
            if affected == Individual.AFFECTED_STATUS_UNAFFECTED and individual.sex == Individual.SEX_MALE:
                genotype = REF_REF

            x_gt_filter = GENOTYPE_QUERY_MAP[genotype](x_sample_ht.GT)
            x_sample_ht = x_sample_ht.filter(x_gt_filter)
            if inheritance_mode == X_LINKED_RECESSIVE:
                return x_sample_ht

        sample_ht = sample_ht.filter(gt_filter)

        if x_sample_ht:
            sample_ht = sample_ht.join(x_sample_ht, how='outer')

        return sample_ht

    def _filter_any_affected_family(self, family_ht, samples, affected_status):
        affected_sample_indices = [
            i for i, sample in enumerate(samples)
            if affected_status[sample.individual.guid] == Individual.AFFECTED_STATUS_AFFECTED
        ]
        if not affected_sample_indices:
            raise InvalidSearchException(
                'At least one affected individual must be included in "Any Affected" search')

        return self._family_has_genotype(family_ht, affected_sample_indices, HAS_ALT)

    def _filter_non_ref_family(self, family_ht, samples, affected_status):
        return self._family_has_genotype(family_ht, range(len(samples)), HAS_ALT)

    def _filter_comp_het_family(self, family_ht, samples, affected_status):
        unaffected_sample_indices = [
            i for i, sample in enumerate(samples)
            if affected_status[sample.individual.guid] == Individual.AFFECTED_STATUS_UNAFFECTED
        ]
        if len(unaffected_sample_indices) < 2:
            return None

        return self._family_has_genotype(family_ht, unaffected_sample_indices, REF_REF)

    @staticmethod
    def _family_has_genotype(family_ht, indices, expected_gt):
        gt_filter = GENOTYPE_QUERY_MAP[expected_gt]
        q = gt_filter(family_ht[f'GT_{indices[0]}'])
        for i in indices[1:]:
            q |= gt_filter(family_ht[f'GT_{i}'])
        return q

    def filter_compound_hets(self, inheritance_filter, annotations_secondary, quality_filter, has_location_filter, keep_main_ht=True):
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
            ch_mt, COMPOUND_HET, inheritance_filter, quality_filter,
            max_families=None if has_location_filter else (MAX_NO_LOCATION_COMP_HET_FAMILIES, 'Location must be specified to search for compound heterozygous variants across many families')
        )
        ch_ht = self._format_results(ch_mt)

        # Get possible pairs of variants within the same gene
        ch_ht = ch_ht.annotate(gene_ids=ch_ht.transcripts.key_set())
        ch_ht = ch_ht.explode(ch_ht.gene_ids)
        ch_ht = ch_ht.group_by('gene_ids').aggregate(v1=hl.agg.collect(ch_ht.row).map(lambda v: v.drop('gene_ids')))
        ch_ht = ch_ht.annotate(v2=ch_ht.v1)
        ch_ht = ch_ht.explode(ch_ht.v1)
        ch_ht = ch_ht.explode(ch_ht.v2)
        ch_ht = ch_ht.filter(ch_ht.v1[VARIANT_KEY_FIELD] != ch_ht.v2[VARIANT_KEY_FIELD])

        # Filter variant pairs for primary/secondary consequences
        if self._allowed_consequences and self._allowed_consequences_secondary:
            ch_ht = self._filter_valid_comp_het_annotation_pairs(ch_ht)

        # Once SVs are integrated: need to handle SNPs in trans with deletions called as hom alt

        # Filter variant pairs for family and genotype
        ch_ht = ch_ht.annotate(family_guids=ch_ht.v1.familyGuids.intersection(ch_ht.v2.familyGuids))
        unaffected_by_family = hl.literal({
            family_guid: [
                guid for guid, affected in affected_status.items() if affected == Individual.AFFECTED_STATUS_UNAFFECTED
            ] for family_guid, affected_status in self._family_individual_affected_status.items()
        })
        ch_ht = ch_ht.annotate(
            family_guids=ch_ht.family_guids.filter(lambda family_guid: unaffected_by_family[family_guid].all(
                lambda i_guid: (ch_ht.v1.genotypes[i_guid].numAlt < 1) | (ch_ht.v2.genotypes[i_guid].numAlt < 1)
            )))
        ch_ht = ch_ht.filter(ch_ht.family_guids.size() > 0)
        ch_ht = ch_ht.annotate(
            v1=ch_ht.v1.annotate(familyGuids=ch_ht.family_guids),
            v2=ch_ht.v2.annotate(familyGuids=ch_ht.family_guids),
        )

        # Format pairs as lists and de-duplicate
        ch_ht = ch_ht.annotate(
            **{GROUPED_VARIANTS_FIELD: hl.sorted([ch_ht.v1, ch_ht.v2])})  # TODO #2496: sort with self._sort
        ch_ht = ch_ht.annotate(
            **{VARIANT_KEY_FIELD: hl.str(':').join(ch_ht[GROUPED_VARIANTS_FIELD].map(lambda v: v[VARIANT_KEY_FIELD]))})
        ch_ht = ch_ht.key_by(VARIANT_KEY_FIELD).select(GROUPED_VARIANTS_FIELD)

        self._comp_het_ht = ch_ht.distinct()

        if not keep_main_ht:
            self._mt = None

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
        if self._consequence_overrides[CLINVAR_KEY]:
            allowed_terms = hl.set(self._consequence_overrides[CLINVAR_KEY])
            has_annotation_filter |= (
                    allowed_terms.contains(ch_ht.v1.clinvar.clinicalSignificance) |
                    allowed_terms.contains(ch_ht.v2.clinvar.clinicalSignificance))
        if self._consequence_overrides[HGMD_KEY]:
            allowed_classes = hl.set(self._consequence_overrides[HGMD_KEY])
            has_annotation_filter |= (
                    allowed_classes.contains(ch_ht.v1.hgmd['class']) |
                    allowed_classes.contains(ch_ht.v2.hgmd['class']))
        if self._consequence_overrides[SPLICE_AI_FIELD]:
            splice_ai = float(self._consequence_overrides[SPLICE_AI_FIELD])
            has_annotation_filter |= (
                    (ch_ht.v1.predictions.splice_ai >= splice_ai) |
                    (ch_ht.v2.predictions.splice_ai >= splice_ai))
        return ch_ht.filter(has_annotation_filter)

    def _format_results(self, mt):
        results = mt.rows()
        results = results.annotate(
            genomeVersion=self._genome_version.replace('GRCh', ''),
            **{k: v(results) for k, v in ANNOTATION_FIELDS.items()},
        )
        response_keys = ['genomeVersion', *CORE_FIELDS, *ANNOTATION_FIELDS.keys()]
        if self._allowed_consequences:
            consequences_set = hl.set(self._allowed_consequences)
            selected_transcript_expr = results.sortedTranscriptConsequences.find(
                lambda t: consequences_set.contains(t.major_consequence)).transcript_id
            if self._allowed_consequences_secondary:
                consequences_secondary_set = hl.set(self._allowed_consequences_secondary)
                selected_transcript_expr = hl.bind(lambda transcript_id: hl.or_else(
                    transcript_id, results.sortedTranscriptConsequences.find(
                        lambda t: consequences_secondary_set.contains(t.major_consequence)).transcript_id),
                                                   selected_transcript_expr)

            results = results.annotate(selectedMainTranscriptId=hl.if_else(
                consequences_set.contains(results.sortedTranscriptConsequences[0].major_consequence),
                hl.missing(hl.dtype('str')), selected_transcript_expr,
            ))
            response_keys.append('selectedMainTranscriptId')

        results = results.key_by(VARIANT_KEY_FIELD)
        return results.select(*response_keys)

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


class VariantHailTableQuery(BaseHailTableQuery):

    def _load_table(self, data_source, intervals=None, exclude_intervals=False):
        mt = super(VariantHailTableQuery, self)._load_table(data_source, intervals=None if exclude_intervals else intervals)
        mt = mt.filter_rows(hl.agg.any(mt.GT.is_non_ref()))
        if intervals and exclude_intervals:
            intervals = self._parse_intervals(intervals)
            mt = hl.filter_intervals(mt, intervals, keep=False)
        return mt


class GcnvHailTableQuery(BaseHailTableQuery):

    def _load_table(self, data_source, intervals=None, exclude_intervals=False):
        mt = super(GcnvHailTableQuery, self)._load_table(data_source)
        # TODO filter no-sample rows
        if intervals:
            intervals = self._parse_intervals(intervals)
            interval_filter = hl.array(intervals).all(lambda interval: not interval.overlaps(mt.interval)) \
                if exclude_intervals else hl.array(intervals).any(lambda interval: interval.overlaps(mt.interval))
            mt = mt.filter_rows(interval_filter)
        return mt


class AllDataTypeHailTableQuery(BaseHailTableQuery):

    def _load_table(self, data_source, **kwargs):
        # TODO does not work, figure out multi-class inheritance
        mt = VariantHailTableQuery._load_table(data_source[Sample.DATASET_TYPE_VARIANT_CALLS], **kwargs)
        sv_mt = GcnvHailTableQuery._load_table(data_source[Sample.DATASET_TYPE_SV_CALLS], **kwargs)

        mt = mt.key_by(VARIANT_KEY_FIELD).join(sv_mt, how='outer')
        transcript_struct_types = mt.sortedTranscriptConsequences.dtype.element_type
        sv_transcript_fields = mt.sortedTranscriptConsequences_1.dtype.element_type.keys()
        missing_transcript_fields = [k for k in TRANSCRIPT_FIELDS if k not in sv_transcript_fields]
        # TODO merge columns?
        return mt.transmute(sortedTranscriptConsequences=hl.or_else(
            mt.sortedTranscriptConsequences.map(
                lambda t: t.select(*sv_transcript_fields, *missing_transcript_fields)),
            hl.array(mt.sortedTranscriptConsequences_1.map(
                lambda t: t.annotate(**{k: hl.missing(transcript_struct_types[k]) for k in missing_transcript_fields})))
        ))
