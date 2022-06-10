from copy import deepcopy
from collections import defaultdict
import hail as hl
import logging

from seqr.views.utils.json_utils import _to_camel_case
from reference_data.models import GENOME_VERSION_GRCh37
from seqr.models import Sample, Individual
from seqr.utils.elasticsearch.utils import InvalidSearchException
from seqr.utils.elasticsearch.constants import RECESSIVE, COMPOUND_HET, X_LINKED_RECESSIVE, ANY_AFFECTED, NEW_SV_FIELD, \
    INHERITANCE_FILTERS, ALT_ALT, REF_REF, REF_ALT, HAS_ALT, HAS_REF, SPLICE_AI_FIELD, MAX_NO_LOCATION_COMP_HET_FAMILIES, \
    CLINVAR_SIGNFICANCE_MAP, HGMD_CLASS_MAP, CLINVAR_PATH_SIGNIFICANCES, CLINVAR_KEY, HGMD_KEY, PATH_FREQ_OVERRIDE_CUTOFF

logger = logging.getLogger(__name__)

AFFECTED = Individual.AFFECTED_STATUS_AFFECTED
UNAFFECTED = Individual.AFFECTED_STATUS_UNAFFECTED

GENOTYPE_QUERY_MAP = {
    REF_REF: lambda gt: gt.is_hom_ref(),
    REF_ALT: lambda gt: gt.is_het(),
    ALT_ALT: lambda gt: gt.is_hom_var(),
    HAS_ALT: lambda gt: gt.is_non_ref(),
    HAS_REF: lambda gt: gt.is_hom_ref() | gt.is_het_ref(),
}

STRUCTURAL_ANNOTATION_FIELD = 'structural'

VARIANT_KEY_FIELD = 'variantId'
GROUPED_VARIANTS_FIELD = 'variants'

class BaseHailTableQuery(object):

    GENOTYPE_FIELDS = {}
    # In production: will not have callset frequency, may rename these fields
    CALLSET_FIELD = 'callset'
    CALLSET_POPULATION = {field.lower(): field for field in ['AF', 'AC', 'AN']}
    POPULATIONS = {}
    PREDICTION_FIELDS_CONFIG = {}
    TRANSCRIPT_FIELDS = ['gene_id', 'major_consequence']
    ANNOTATION_OVERRIDE_FIELDS = []

    CORE_FIELDS = ['genotypes']
    BASE_ANNOTATION_FIELDS = {
        'familyGuids': lambda r: hl.array(r.familyGuids),
        'liftedOverGenomeVersion': lambda r: hl.if_else(  # In production - format all rg37_locus fields in main HT?
            hl.is_defined(r.rg37_locus), hl.literal(GENOME_VERSION_GRCh37), hl.missing(hl.dtype('str')), # TODO #2716: rg37_locus will be missing for build 37
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
            'populations': lambda r: hl.struct(
                **{self.CALLSET_FIELD: hl.struct(**{key: r[field] for key, field in self.CALLSET_POPULATION.items()})}, **{
                population: hl.struct(**{
                    response_key: hl.or_else(r[population][field], 0) for response_key, field in pop_config.items()
                    if field is not None
                }) for population, pop_config in self.populations_configs.items()}),
            'predictions': lambda r: hl.struct(**{
                prediction: r[path[0]][path[1]] for prediction, path in self.PREDICTION_FIELDS_CONFIG.items()
            }),
            'transcripts': lambda r: r.sortedTranscriptConsequences.map(
                lambda t: hl.struct(**{_to_camel_case(k): t[k] for k in self.TRANSCRIPT_FIELDS})).group_by(
                lambda t: t.geneId),
        }
        annotation_fields.update(self.BASE_ANNOTATION_FIELDS)
        return annotation_fields

    def __init__(self, data_source, samples, genome_version, **kwargs):
        self._genome_version = genome_version
        self._samples_by_id = {s.sample_id: s for s in samples}
        self._affected_status_samples = defaultdict(set)
        self._comp_het_ht = None
        self._allowed_consequences = None
        self._allowed_consequences_secondary = None
        self._consequence_overrides = {
            CLINVAR_KEY: set(), HGMD_KEY: set(), SPLICE_AI_FIELD: None,
            NEW_SV_FIELD: None, STRUCTURAL_ANNOTATION_FIELD: None,
        }

        self._mt = self._load_table(data_source, **kwargs)

    def _load_table(self, data_source, intervals=None, **kwargs):
        load_table_kwargs = {'_intervals': self._parse_intervals(intervals), '_filter_intervals': bool(intervals)}
        ht = hl.read_table(f'/hail_datasets/{data_source}.ht', **load_table_kwargs)
        sample_hts = {
            sample_id: hl.read_table(f'/hail_datasets/{data_source}_samples/{sample_id}.ht', **load_table_kwargs)
            for sample_id in self._samples_by_id.keys()
        }
        ht = ht.annotate(**{sample_id: s_ht[ht.key] for sample_id, s_ht in sample_hts.items()})
        mt = ht.to_matrix_table_row_major(list(sample_hts.keys()), col_field_name='s')
        return mt.filter_rows(hl.agg.any(mt.GT.is_non_ref()))

    def _parse_intervals(self, intervals):
        if intervals:
            intervals = [hl.eval(hl.parse_locus_interval(interval, reference_genome=self._genome_version))
                         for interval in intervals]
        return intervals

    def filter_variants(self, rs_ids=None, frequencies=None, pathogenicity=None, in_silico=None,
                        annotations=None, quality_filter=None, custom_query=None):
        self._parse_pathogenicity_overrides(pathogenicity)
        self._parse_annotations_overrides(annotations)

        if rs_ids:
            self._filter_rsids(rs_ids)

        self._filter_custom(custom_query)

        self._filter_by_frequency(frequencies)

        self._filter_by_in_silico(in_silico)

        if quality_filter.get('vcf_filter') is not None:
            self._filter_vcf_filters()

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
        callset_filter = (frequencies or {}).pop(self.CALLSET_FIELD, {}) or {}
        frequencies = {k: v for k, v in (frequencies or {}).items() if k in self.populations_configs}
        if not (callset_filter or frequencies):
            return

        clinvar_path_terms = [f for f in self._consequence_overrides[CLINVAR_KEY] if f in CLINVAR_PATH_SIGNIFICANCES]
        has_path_override = bool(clinvar_path_terms) and any(
            freqs.get('af') or 1 < PATH_FREQ_OVERRIDE_CUTOFF for freqs in frequencies.values())

        if callset_filter.get('af') is not None:
            callset_f = self._mt[self.CALLSET_POPULATION['af']] <= callset_filter['af']
            if has_path_override and callset_filter['af'] < PATH_FREQ_OVERRIDE_CUTOFF:
                callset_f |= (
                        self._get_clinvar_filter(clinvar_path_terms) &
                        (self._mt[self.CALLSET_POPULATION['af']] <= PATH_FREQ_OVERRIDE_CUTOFF)
                )
            self._mt = self._mt.filter_rows(callset_f)
        elif callset_filter.get('ac') is not None:
            self._mt = self._mt.filter_rows(self._mt[self.CALLSET_POPULATION['ac']] <= callset_filter['ac'])

        for pop, freqs in sorted(frequencies.items()):
            pop_filter = None
            if freqs.get('af') is not None:
                af_field = self.populations_configs[pop].get('filter_af') or self.populations_configs[pop]['af']
                pop_filter = self._mt[pop][af_field] <= freqs['af']
                if has_path_override and freqs['af'] < PATH_FREQ_OVERRIDE_CUTOFF:
                    pop_filter |= (
                            self._get_clinvar_filter(clinvar_path_terms) &
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
            if k in self.PREDICTION_FIELDS_CONFIG and v is not None and len(v) != 0
        }
        if not in_silico_filters:
            return

        in_silico_q = None
        missing_in_silico_q = None
        for in_silico, value in in_silico_filters.items():
            ht_value = self._get_in_silico_ht_field(in_silico)
            try:
                float_val = float(value)
                if ht_value.dtype == hl.tstr:
                    # In production: store all numeric scores as floats
                    ht_value = hl.parse_float(ht_value)
                score_filter = ht_value >= float_val
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
        score_path = self.PREDICTION_FIELDS_CONFIG[in_silico]
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
        if self._consequence_overrides[STRUCTURAL_ANNOTATION_FIELD]:
            allowed_sv_types = hl.set(self._consequence_overrides[STRUCTURAL_ANNOTATION_FIELD])
            annotation_filters.append(allowed_sv_types.contains(self._mt.svType))

        if allowed_consequences:
            annotation_filters.append(
                self._get_consequence_terms().any(lambda ct: hl.set(allowed_consequences).contains(ct))
            )

        if not annotation_filters:
            return self._mt
        annotation_filter = annotation_filters[0]
        for af in annotation_filters[1:]:
            annotation_filter |= af

        return self._mt.filter_rows(annotation_filter)

    def _get_consequence_terms(self):
        return self._mt.sortedTranscriptConsequences.map(lambda tc: tc.major_consequence)

    def _get_clinvar_filter(self, clinvar_terms):
        allowed_significances = hl.set(clinvar_terms)
        return allowed_significances.contains(self._mt.clinvar.clinical_significance)

    def annotate_filtered_genotypes(self, *args):
        self._mt = self._filter_by_genotype(self._mt, *args)

    def _filter_by_genotype(self, mt, inheritance_mode, inheritance_filter, quality_filter, max_families=None):
        individual_affected_status = inheritance_filter.get('affected') or {}
        if inheritance_mode == ANY_AFFECTED:
            inheritance_filter = None
        elif inheritance_mode:
            inheritance_filter.update(INHERITANCE_FILTERS[inheritance_mode])

        if (inheritance_filter or inheritance_mode) and not self._affected_status_samples:
            self._set_validated_affected_status(individual_affected_status, max_families)

        sample_family_map = hl.dict({sample_id: s.individual.family.guid for sample_id, s in self._samples_by_id.items()})
        mt = mt.annotate_rows(familyGuids=self._get_matched_families_expr(
            mt, inheritance_mode, inheritance_filter, sample_family_map,
            self._get_quality_filter_expr(mt, quality_filter),
        ))

        if inheritance_mode == X_LINKED_RECESSIVE:
            mt = mt.filter_rows(self._get_x_chrom_filter(mt))
        elif inheritance_mode == RECESSIVE:
            x_chrom_filter = self._get_x_chrom_filter(mt)
            quality_filter_expr = self._get_quality_filter_expr(mt, quality_filter)
            if quality_filter_expr is not None:
                x_chrom_filter &= quality_filter_expr
            mt = mt.annotate_rows(xLinkedfamilies=self._get_matched_families_expr(
                mt, X_LINKED_RECESSIVE, inheritance_filter, sample_family_map, x_chrom_filter,
            ))
            mt = mt.transmute_rows(familyGuids=mt.familyGuids.union(mt.xLinkedfamilies))
        elif inheritance_mode == COMPOUND_HET:
            unaffected_samples_by_family = defaultdict(set)
            for sample_id in self._affected_status_samples[UNAFFECTED]:
                unaffected_samples_by_family[self._samples_by_id[sample_id].individual.family.guid].add(sample_id)
            unaffected_samples_by_family = {k: v for k, v in unaffected_samples_by_family.items() if len(v) > 1}
            if unaffected_samples_by_family:
                # remove variants where all unaffected individuals are het
                mt = mt.annotate_rows(notPhasedFamilies=self._get_family_all_samples_expr(
                    mt, mt.GT.is_het(), hl.dict(unaffected_samples_by_family)))
                mt = mt.transmute_rows(familyGuids=mt.familyGuids.difference(mt.notPhasedFamilies))

        mt = mt.filter_rows(mt.familyGuids.size() > 0)

        sample_individual_map = hl.dict({sample_id: s.individual.guid for sample_id, s in self._samples_by_id.items()})
        mt = mt.annotate_rows(genotypes=hl.agg.filter(
            mt.familyGuids.contains(sample_family_map[mt.s]),
            hl.agg.collect(hl.struct(
                individualGuid=sample_individual_map[mt.s],
                sampleId=mt.s,
                numAlt=mt.GT.n_alt_alleles(),
                **{k: mt[f] for k, f in self.GENOTYPE_FIELDS.items()}
            ))))
        return self._format_genotypes(mt)

    def _format_genotypes(self, mt):
        return mt.annotate_rows(genotypes=mt.genotypes.group_by(lambda x: x.individualGuid).map_values(lambda x: x[0]))

    def _set_validated_affected_status(self, individual_affected_status, max_families):
        for sample_id, sample in self._samples_by_id.items():
            affected = individual_affected_status.get(sample.individual.guid) or sample.individual.affected
            self._affected_status_samples[affected].add(sample_id)

        if not self._affected_status_samples[AFFECTED]:
            raise InvalidSearchException(
                'Inheritance based search is disabled in families with no data loaded for affected individuals')

        affected_families = {
            self._samples_by_id[sample_id].individual.family for sample_id in self._affected_status_samples[AFFECTED]
        }
        self._samples_by_id = {
            sample_id: s for sample_id, s in self._samples_by_id.items() if s.individual.family in affected_families
        }
        if max_families and len(affected_families) > max_families[0]:
            raise InvalidSearchException(max_families[1])

    def _get_quality_filter_expr(self, mt, quality_filter):
        quality_filter_expr = None
        for filter_k, value in (quality_filter or {}).items():
            field = self.GENOTYPE_FIELDS.get(filter_k.replace('min_', ''))
            if field:
                field_filter = mt[field] > value
                if quality_filter_expr is None:
                    quality_filter_expr = field_filter
                else:
                    quality_filter_expr &= field_filter

        return quality_filter_expr

    def _get_x_chrom_filter(self, mt):
        # TODO #2716: format chromosome for genome build
        return mt.locus.contig == 'chrX'

    def _get_matched_families_expr(self, mt, inheritance_mode, inheritance_filter, sample_family_map, quality_filter_expr):
        if not inheritance_filter:
            sample_filter = mt.GT.is_non_ref()
            if quality_filter_expr is not None:
                sample_filter &= quality_filter_expr
            if inheritance_mode == ANY_AFFECTED:
                sample_filter &= hl.set(self._affected_status_samples[AFFECTED]).contains(mt.s)
            return hl.agg.filter(sample_filter, hl.agg.collect_as_set(sample_family_map[mt.s]))

        search_sample_ids = set()
        sample_filters = []

        individual_genotype_filter = (inheritance_filter or {}).get('genotype')
        if individual_genotype_filter:
            samples_by_individual = {s.individual.guid: sample_id for sample_id, s in self._samples_by_id.items()}
            samples_by_gentotype = defaultdict(set)
            for individual_guid, genotype in individual_genotype_filter.items():
                sample_id = samples_by_individual.get(individual_guid)
                if sample_id:
                    search_sample_ids.add(sample_id)
                    samples_by_gentotype[genotype].add(sample_id)
            sample_filters += list(samples_by_gentotype.items())

        for status, status_samples in self._affected_status_samples.items():
            status_sample_ids = status_samples - search_sample_ids
            if inheritance_mode == X_LINKED_RECESSIVE and status == UNAFFECTED:
                male_sample_ids = {
                    sample_id for sample_id in status_sample_ids
                    if self._samples_by_id[sample_id].individual.sex == Individual.SEX_MALE
                }
                if male_sample_ids:
                    status_sample_ids -= male_sample_ids
                    sample_filters.append((REF_REF, male_sample_ids))
            if status_sample_ids and inheritance_filter.get(status):
                search_sample_ids.update(status_sample_ids)
                sample_filters.append((inheritance_filter[status], status_sample_ids))

        sample_ids_by_family = defaultdict(set)
        for sample_id in search_sample_ids:
            sample = self._samples_by_id[sample_id]
            sample_ids_by_family[sample.individual.family.guid].add(sample_id)
        family_samples_map = hl.dict(sample_ids_by_family)

        sample_filter_exprs = [
            (GENOTYPE_QUERY_MAP[genotype](mt.GT) & hl.set(samples).contains(mt.s))
            for genotype, samples in sample_filters
        ]
        sample_filter = sample_filter_exprs[0]
        for sub_filter in sample_filter_exprs[1:]:
            sample_filter |= sub_filter

        if quality_filter_expr is not None:
            sample_filter &= quality_filter_expr

        return self._get_family_all_samples_expr(mt, sample_filter, family_samples_map)

    @staticmethod
    def _get_family_all_samples_expr(mt, sample_filter, family_samples_map):
        return hl.bind(
            lambda samples: family_samples_map.key_set().filter(lambda f: family_samples_map[f].is_subset(samples)),
            hl.agg.filter(sample_filter, hl.agg.collect_as_set(mt.s)))

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

        # TODO #2663 Once SVs are integrated: need to handle SNPs in trans with deletions called as hom alt

        # Filter variant pairs for family and genotype
        ch_ht = ch_ht.annotate(family_guids=hl.set(ch_ht.v1.familyGuids).intersection(hl.set(ch_ht.v2.familyGuids)))
        unaffected_family_individuals = defaultdict(set)
        for sample_id in self._affected_status_samples[UNAFFECTED]:
            individual = self._samples_by_id[sample_id].individual
            unaffected_family_individuals[individual.family.guid].add(individual.guid)
        ch_ht = ch_ht.annotate(
            family_guids=ch_ht.family_guids.filter(lambda family_guid: hl.dict(unaffected_family_individuals)[family_guid].all(
                lambda i_guid: (ch_ht.v1.genotypes[i_guid].numAlt < 1) | (ch_ht.v2.genotypes[i_guid].numAlt < 1)
            )))
        ch_ht = ch_ht.filter(ch_ht.family_guids.size() > 0)
        ch_ht = ch_ht.annotate(
            v1=ch_ht.v1.annotate(familyGuids=hl.array(ch_ht.family_guids)),
            v2=ch_ht.v2.annotate(familyGuids=hl.array(ch_ht.family_guids)),
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
        # TODO share override code with _filter_by_annotations
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
        if self._consequence_overrides[STRUCTURAL_ANNOTATION_FIELD]:
            allowed_sv_types = hl.set(self._consequence_overrides[STRUCTURAL_ANNOTATION_FIELD])
            has_annotation_filter |= (
                    allowed_sv_types.contains(ch_ht.v1.svType) |
                    allowed_sv_types.contains(ch_ht.v2.svType))
        return ch_ht.filter(has_annotation_filter)

    def _format_results(self, mt):
        results = mt.rows()
        results = results.annotate(
            genomeVersion=self._genome_version.replace('GRCh', ''),
            **{k: v(results) for k, v in self.annotation_fields.items()},
        )
        results = results.annotate(
            **{k: v(self, results) for k, v in self.COMPUTED_ANNOTATION_FIELDS.items()},
        )
        results = results.key_by(VARIANT_KEY_FIELD)
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


class VariantHailTableQuery(BaseHailTableQuery):

    GENOTYPE_FIELDS = {f.lower(): f for f in ['AB', 'AD', 'DP', 'PL', 'GQ']}
    POPULATIONS = {
        'topmed': {'hemi': None, 'het': None},
        'g1k': {'filter_af': 'POPMAX_AF', 'hom': None, 'hemi': None, 'het': None},
        'exac': {
            'filter_af': 'AF_POPMAX', 'ac': 'AC_Adj', 'an': 'AN_Adj', 'hom': 'AC_Hom', 'hemi': 'AC_Hemi', 'het': None,
        },
        'gnomad_exomes': {'filter_AF': 'AF_POPMAX_OR_GLOBAL', 'het': None},
        'gnomad_genomes': {'filter_af': 'AF_POPMAX_OR_GLOBAL', 'het': None},
    }
    PREDICTION_FIELDS_CONFIG = {
        'cadd': ('cadd', 'PHRED'),
        'fathmm': ('dbnsfp', 'FATHMM_pred'),
        'gerp_rs': ('dbnsfp', 'GERP_RS'),
        'metasvm': ('dbnsfp', 'MetaSVM_pred'),
        'mutationtaster': ('dbnsfp', 'MutationTaster_pred'),
        'phastcons_100_vert': ('dbnsfp', 'phastCons100way_vertebrate'),
        'polyphen': ('dbnsfp', 'Polyphen2_HVAR_pred'),
        'revel': ('dbnsfp', 'REVEL_score'),
        'sift': ('dbnsfp', 'SIFT_pred'),
        'eigen': ('eigen', 'Eigen_phred'),
        'mpc': ('mpc', 'MPC'),
        'primate_ai': ('primate_ai', 'score'),
        'splice_ai': ('splice_ai', 'delta_score'),
        'splice_ai_consequence': ('splice_ai', 'splice_consequence'),
    }
    TRANSCRIPT_FIELDS = BaseHailTableQuery.TRANSCRIPT_FIELDS + [
        'amino_acids', 'biotype', 'canonical', 'codons', 'hgvsc', 'hgvsp', 'lof', 'lof_flags', 'lof_filter', 'lof_info',
        'transcript_id', 'transcript_rank',
    ]
    ANNOTATION_OVERRIDE_FIELDS = [SPLICE_AI_FIELD]

    CORE_FIELDS = BaseHailTableQuery.CORE_FIELDS + ['hgmd', 'rsid', 'xpos']
    BASE_ANNOTATION_FIELDS = {
        'chrom': lambda r: r.locus.contig.replace("^chr", ""),
        'pos': lambda r: r.locus.position,
        'ref': lambda r: r.alleles[0],
        'alt': lambda r: r.alleles[1],
        'clinvar': lambda r: hl.struct(  # In production - format in main HT?
            clinicalSignificance=r.clinvar.clinical_significance,
            alleleId=r.clinvar.allele_id,
            goldStars=r.clinvar.gold_stars,
        ),
        'genotypeFilters': lambda r: hl.str(' ,').join(r.filters),  # In production - format in main HT?
        'mainTranscriptId': lambda r: r.sortedTranscriptConsequences[0].transcript_id,
        'originalAltAlleles': lambda r: r.originalAltAlleles.map(lambda a: a.split('-')[-1]), # In production - format in main HT
    }
    BASE_ANNOTATION_FIELDS.update(BaseHailTableQuery.BASE_ANNOTATION_FIELDS)

    def _selected_main_transcript_expr(self, results):
        if not self._allowed_consequences:
            return hl.missing(hl.dtype('str'))

        consequences_set = hl.set(self._allowed_consequences)
        selected_transcript_expr = results.sortedTranscriptConsequences.find(
            lambda t: consequences_set.contains(t.major_consequence)).transcript_id
        if self._allowed_consequences_secondary:
            consequences_secondary_set = hl.set(self._allowed_consequences_secondary)
            selected_transcript_expr = hl.bind(
                lambda transcript_id: hl.or_else(
                    transcript_id, results.sortedTranscriptConsequences.find(
                        lambda t: consequences_secondary_set.contains(t.major_consequence)).transcript_id),
                selected_transcript_expr)

        return hl.if_else(
            consequences_set.contains(results.sortedTranscriptConsequences[0].major_consequence),
            hl.missing(hl.dtype('str')), selected_transcript_expr,
        )
    COMPUTED_ANNOTATION_FIELDS = {
        'selectedMainTranscriptId': _selected_main_transcript_expr,
    }

    def _load_table(self, data_source, intervals=None, exclude_intervals=False):
        mt = super(VariantHailTableQuery, self)._load_table(data_source, intervals=None if exclude_intervals else intervals)
        if intervals and exclude_intervals:
            intervals = self._parse_intervals(intervals)
            mt = hl.filter_intervals(mt, intervals, keep=False)
        return mt

    def _get_consequence_terms(self):
        return self._mt.sortedTranscriptConsequences.flatmap(lambda tc: tc.consequence_terms)

    def _get_quality_filter_expr(self, mt, quality_filter):
        min_ab = (quality_filter or {}).get('min_ab')
        quality_filter = {k: v for k, v in quality_filter or {} if k != 'min_ab'}
        quality_filter_expr = super(VariantHailTableQuery, self)._get_quality_filter_expr(mt, quality_filter)
        if min_ab:
            #  AB only relevant for hets
            ab_expr = (~mt.GT.is_het() | (mt.AB > (min_ab / 100)))
            if quality_filter_expr is None:
                quality_filter_expr = ab_expr
            else:
                quality_filter_expr &= ab_expr

        return quality_filter_expr


def _no_genotype_override(genotypes, field):
    return genotypes.values().any(lambda g: (g.numAlt > 0) & hl.is_missing(g[field]))

def _get_genotype_override_field(genotypes, default, field, agg):
    return hl.if_else(
        _no_genotype_override(genotypes, field), default, agg(genotypes.values().map(lambda g: g[field]))
    )

class GcnvHailTableQuery(BaseHailTableQuery):

    GENOTYPE_FIELDS = {
        f: f for f in ['start', 'end', 'numExon', 'geneIds', 'cn', 'qs', 'defragged', 'prevCall', 'prevOverlap', 'newCall']
    }
    CALLSET_FIELD = 'sv_callset'
    CALLSET_POPULATION = {'af': 'sf', 'ac': 'sc', 'an': 'sn'}
    PREDICTION_FIELDS_CONFIG = {
        'strvctvre': ('strvctvre', 'score'),
    }

    BASE_ANNOTATION_FIELDS = {
        'chrom': lambda r: r.interval.start.contig.replace('^chr', ''),
        'pos': lambda r: _get_genotype_override_field(r.genotypes, r.interval.start.position, 'start', hl.min),
        'end': lambda r: _get_genotype_override_field(r.genotypes, r.interval.end.position, 'end', hl.max),
        'numExon': lambda r: _get_genotype_override_field(r.genotypes, r.numExon, 'numExon', hl.max),
        'rg37LocusEnd': lambda r: hl.struct(contig=r.rg37_locus_end.contig, position=r.rg37_locus_end.position),
        'svType': lambda r: r.svType.replace('^gCNV_', ''),
    }
    BASE_ANNOTATION_FIELDS.update(BaseHailTableQuery.BASE_ANNOTATION_FIELDS)
    COMPUTED_ANNOTATION_FIELDS = {
        'transcripts': lambda self, r: hl.if_else(
            _no_genotype_override(r.genotypes, 'geneIds'), r.transcripts, hl.bind(
                lambda gene_ids: hl.dict(r.transcripts.items().filter(lambda t: gene_ids.contains(t[0]))),
                r.genotypes.values().flatmap(lambda g: g.geneIds)
            ),
        )
    }
    ANNOTATION_OVERRIDE_FIELDS = [NEW_SV_FIELD, STRUCTURAL_ANNOTATION_FIELD]

    def _load_table(self, data_source, intervals=None, exclude_intervals=False):
        mt = super(GcnvHailTableQuery, self)._load_table(data_source)
        if intervals:
            intervals = self._parse_intervals(intervals)
            interval_filter = hl.array(intervals).all(lambda interval: not interval.overlaps(mt.interval)) \
                if exclude_intervals else hl.array(intervals).any(lambda interval: interval.overlaps(mt.interval))
            mt = mt.filter_rows(interval_filter)
        return mt

    def _parse_pathogenicity_overrides(self, pathogenicity):
        pass

    def _filter_vcf_filters(self):
        pass

    def _filter_rsids(self, rs_ids):
        raise InvalidSearchException('Variant ID search disabled for SVs')

    def filter_by_variant_ids(self, variant_ids):
        raise InvalidSearchException('Variant ID search disabled for SVs')

    def _get_x_chrom_filter(self, mt):
        # TODO #2716: format chromosome for genome build
        x_chrom_interval = hl.parse_locus_interval('chrX', reference_genome=self._genome_version)
        return mt.interval.overlaps(x_chrom_interval)

    def _get_matched_families_expr(self, mt, inheritance_mode, inheritance_filter, sample_family_map, quality_filter_expr):
        families_expr = super(GcnvHailTableQuery, self)._get_matched_families_expr(
            mt, inheritance_mode, inheritance_filter, sample_family_map, quality_filter_expr)
        if self._consequence_overrides[NEW_SV_FIELD]:
            families_expr = hl.bind(
                lambda families, new_call_families: new_call_families.intersection(families),
                families_expr,
                hl.agg.filter(mt.newCall, hl.agg.collect_as_set(sample_family_map[mt.s])),
            )
        return families_expr

    def _format_genotypes(self, mt):
        individual_map = {}
        family_individuals = defaultdict(set)
        for sample_id, s in self._samples_by_id.items():
            i_guid = s.individual.guid
            individual_map[i_guid] = sample_id
            family_individuals[s.individual.family.guid].add(i_guid)

        #  gCNV data has no ref/ref calls, so add them for all individuals missing from matched families
        matched_individuals = hl.set(mt.genotypes.map(lambda g: g.individualGuid))
        missing_individuals = hl.array(mt.familyGuids.flatmap(lambda f: hl.dict(family_individuals)[f]).filter(
            lambda i: ~matched_individuals.contains(i)))
        genotype_struct_types = mt.genotypes.dtype.element_type
        mt = mt.annotate_rows(genotypes=mt.genotypes.extend(missing_individuals.map(lambda i: hl.struct(
            individualGuid=i,
            sampleId=hl.dict(individual_map)[i],
            numAlt=0,
            **{k: hl.missing(genotype_struct_types[k]) for k in self.GENOTYPE_FIELDS.keys()}
        ))))
        return super(GcnvHailTableQuery, self)._format_genotypes(mt)


class AllDataTypeHailTableQuery(BaseHailTableQuery):

    def _load_table(self, data_source, **kwargs):
        # TODO does not work, figure out multi-class inheritance
        mt = VariantHailTableQuery._load_table(data_source[Sample.DATASET_TYPE_VARIANT_CALLS], **kwargs)
        sv_mt = GcnvHailTableQuery._load_table(data_source[Sample.DATASET_TYPE_SV_CALLS], **kwargs)

        mt = mt.key_by(VARIANT_KEY_FIELD).join(sv_mt, how='outer')
        transcript_struct_types = mt.sortedTranscriptConsequences.dtype.element_type
        missing_transcript_fields = set(VariantHailTableQuery.TRANSCRIPT_FIELDS) - set(GcnvHailTableQuery.TRANSCRIPT_FIELDS)
        # TODO merge columns?
        return mt.transmute(sortedTranscriptConsequences=hl.or_else(
            mt.sortedTranscriptConsequences.map(lambda t: t.select(*VariantHailTableQuery.TRANSCRIPT_FIELDS)),
            hl.array(mt.sortedTranscriptConsequences_1.map(
                lambda t: t.annotate(**{k: hl.missing(transcript_struct_types[k]) for k in missing_transcript_fields})))
        ))
