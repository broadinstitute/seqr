from collections import defaultdict
import hail as hl
import logging

from seqr.views.utils.json_utils import _to_camel_case
from reference_data.models import GENOME_VERSION_GRCh37
from seqr.models import Sample, Individual
from seqr.utils.elasticsearch.utils import InvalidSearchException
from seqr.utils.elasticsearch.constants import RECESSIVE, COMPOUND_HET, X_LINKED_RECESSIVE, ANY_AFFECTED, \
    INHERITANCE_FILTERS, ALT_ALT, REF_REF, REF_ALT, HAS_ALT, HAS_REF, MAX_NO_LOCATION_COMP_HET_FAMILIES, SPLICE_AI_FIELD, \
    CLINVAR_SIGNFICANCE_MAP, HGMD_CLASS_MAP, CLINVAR_PATH_SIGNIFICANCES, CLINVAR_KEY, HGMD_KEY, PATH_FREQ_OVERRIDE_CUTOFF
from seqr.utils.elasticsearch.es_search import EsSearch, _get_family_affected_status

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

GENOTYPE_FIELDS = ['familyGuids', 'genotypes']
CORE_FIELDS = ['hgmd', 'rsid', 'xpos']
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

    def __init__(self, data_source, genome_version, **kwargs):
        self._genome_version = genome_version
        self._comp_het_ht = None
        self._allowed_consequences = None
        self._allowed_consequences_secondary = None
        self._consequence_overrides = {CLINVAR_KEY: set(), HGMD_KEY: set(), SPLICE_AI_FIELD: None}

        self._ht = self._load_table(data_source, **kwargs)

    def _load_table(self, data_source, intervals=None, **kwargs):
        return hl.read_table(
            f'/hail_datasets/{data_source}.ht',
            _intervals=self._parse_intervals(intervals),
            _filter_intervals=bool(intervals),
        )

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
        self._ht = self._ht.filter(hl.set(rs_ids).contains(self._ht.rsid))

    def _filter_vcf_filters(self):
        self._ht = self._ht.filter(self._ht.filters.length() < 1)

    def filter_main_annotations(self):
        self._ht = self._filter_by_annotations(self._allowed_consequences)

    def filter_by_variant_ids(self, variant_ids):
        if len(variant_ids) == 1:
            self._ht = self._ht.filter(self._ht.alleles == [variant_ids[0][2], variant_ids[0][3]])
        else:
            id_q = self._variant_id_q(*variant_ids[0])
            for variant_id in variant_ids[1:]:
                id_q |= self._variant_id_q(*variant_id)

    def _variant_id_q(self, chrom, pos, ref, alt):
        # TODO #2716: format chromosome for genome build
        return (self._ht.locus == hl.locus(f'chr{chrom}', pos, reference_genome=self._genome_version)) & (
                    self._ht.alleles == [ref, alt])

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
            callset_f = self._ht.AF <= callset_filter['af']
            if has_path_override and callset_filter['af'] < PATH_FREQ_OVERRIDE_CUTOFF:
                callset_f |= (
                        self._get_clinvar_filter(clinvar_path_terms) &
                        (self._ht.AF <= PATH_FREQ_OVERRIDE_CUTOFF)
                )
            self._ht = self._ht.filter(callset_f)
        elif callset_filter.get('ac') is not None:
            self._ht = self._ht.filter(self._ht.AC <= callset_filter['ac'])

        for pop, freqs in sorted(frequencies.items()):
            pop_filter = None
            if freqs.get('af') is not None:
                af_field = POPULATIONS[pop].get('filter_af') or POPULATIONS[pop]['af']
                pop_filter = self._ht[pop][af_field] <= freqs['af']
                if has_path_override and freqs['af'] < PATH_FREQ_OVERRIDE_CUTOFF:
                    pop_filter |= (
                            self._get_clinvar_filter(clinvar_path_terms) &
                            (self._ht[pop][af_field] <= PATH_FREQ_OVERRIDE_CUTOFF)
                    )
            elif freqs.get('ac') is not None:
                ac_field = POPULATIONS[pop]['ac']
                if ac_field:
                    pop_filter = self._ht[pop][ac_field] <= freqs['ac']

            if freqs.get('hh') is not None:
                hom_field = POPULATIONS[pop]['hom']
                hemi_field = POPULATIONS[pop]['hemi']
                if hom_field:
                    hh_filter = self._ht[pop][hom_field] <= freqs['hh']
                    if pop_filter is None:
                        pop_filter = hh_filter
                    else:
                        pop_filter &= hh_filter
                if hemi_field:
                    hh_filter = self._ht[pop][hemi_field] <= freqs['hh']
                    if pop_filter is None:
                        pop_filter = hh_filter
                    else:
                        pop_filter &= hh_filter

            if pop_filter is not None:
                self._ht = self._ht.filter(hl.is_missing(self._ht[pop]) | pop_filter)

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

        self._ht = self._ht.filter(in_silico_q | missing_in_silico_q)

    def _get_in_silico_ht_field(self, in_silico):
        score_path = PREDICTION_FIELDS_CONFIG[in_silico]
        return self._ht[score_path[0]][score_path[1]]

    def _filter_by_annotations(self, allowed_consequences):
        annotation_filters = []

        if self._consequence_overrides[CLINVAR_KEY]:
            annotation_filters.append(self._get_clinvar_filter(self._consequence_overrides[CLINVAR_KEY]))
        if self._consequence_overrides[HGMD_KEY]:
            allowed_classes = hl.set(self._consequence_overrides[HGMD_KEY])
            annotation_filters.append(allowed_classes.contains(self._ht.hgmd['class']))
        if self._consequence_overrides[SPLICE_AI_FIELD]:
            annotation_filters.append(
                self._get_in_silico_ht_field(SPLICE_AI_FIELD) >= float(self._consequence_overrides[SPLICE_AI_FIELD]))

        if allowed_consequences:
            annotation_filters.append(self._get_filtered_transcript_consequences(allowed_consequences))

        if not annotation_filters:
            return self._ht
        annotation_filter = annotation_filters[0]
        for af in annotation_filters[1:]:
            annotation_filter |= af

        return self._ht.filter(annotation_filter)

    def _get_filtered_transcript_consequences(self, allowed_consequences):
        allowed_consequences_set = hl.set(allowed_consequences)
        consequence_terms = self._ht.sortedTranscriptConsequences.flatmap(lambda tc: tc.consequence_terms)
        return consequence_terms.any(lambda ct: allowed_consequences_set.contains(ct))

    def _get_clinvar_filter(self, clinvar_terms):
        allowed_significances = hl.set(clinvar_terms)
        return allowed_significances.contains(self._ht.clinvar.clinical_significance)

    def annotate_filtered_genotypes(self, *args):
        self._ht = self._ht.join(self._filter_by_genotype(*args))

    def _filter_by_genotype(self, samples_by_family, family_individual_affected_status, inheritance_mode, inheritance_filter,
                            quality_filter):
        if inheritance_mode == ANY_AFFECTED:
            inheritance_filter = None
        elif inheritance_mode:
            inheritance_filter.update(INHERITANCE_FILTERS[inheritance_mode])

        family_filter = None
        if inheritance_mode == COMPOUND_HET:
            family_filter = self._filter_comp_het_family
        elif inheritance_mode == ANY_AFFECTED:
            family_filter = self._filter_any_affected_family
        elif not inheritance_filter:
            family_filter = self._filter_non_ref_family

        family_guids = sorted(samples_by_family.keys())
        family_hts = [
            self._get_filtered_family_table(
                samples=list(samples_by_family[family_guid].values()), affected_status=family_individual_affected_status.get(family_guid),
                inheritance_mode=inheritance_mode, inheritance_filter=inheritance_filter, quality_filter=quality_filter,
                family_filter=family_filter)
            for family_guid in family_guids
        ]

        genotype_ht = family_hts[0]
        for family_ht in family_hts[1:]:
            genotype_ht = genotype_ht.join(family_ht, how='outer')
        genotype_ht = genotype_ht.rename({'genotypes': 'genotypes_0'})

        return genotype_ht.annotate(
            familyGuids=hl.array([
                hl.if_else(hl.is_defined(genotype_ht[f'genotypes_{i}']), family_guid, hl.missing(hl.tstr))
                for i, family_guid in enumerate(family_guids)
            ]).filter(lambda x: hl.is_defined(x)),
            genotypes=hl.array([
                genotype_ht[f'genotypes_{i}'] for i in range(len(family_guids))
            ]).flatmap(lambda x: x).filter(lambda x: hl.is_defined(x)).group_by(lambda x: x.individualGuid).map_values(
                lambda x: x[0]),
        ).select(*GENOTYPE_FIELDS)

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

    def filter_compound_hets(self, samples_by_family, family_individual_affected_status, annotations_secondary, quality_filter,
                             keep_main_ht=True):
        if not self._allowed_consequences:
            raise InvalidSearchException('Annotations must be specified to search for compound heterozygous variants')

        # Filter and format variants
        comp_het_consequences = set(self._allowed_consequences)
        if annotations_secondary:
            self._allowed_consequences_secondary = sorted(
                {ann for anns in annotations_secondary.values() for ann in anns})
            comp_het_consequences.update(self._allowed_consequences_secondary)

        ch_ht = self._filter_by_annotations(comp_het_consequences)
        ch_ht = ch_ht.join(self._filter_by_genotype(
            samples_by_family, family_individual_affected_status, inheritance_mode=COMPOUND_HET, inheritance_filter={},
            quality_filter=quality_filter,
        ))
        ch_ht = self._format_results(ch_ht)

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
        ch_ht = ch_ht.annotate(family_guids=hl.set(ch_ht.v1.familyGuids).intersection(hl.set(ch_ht.v2.familyGuids)))
        unaffected_by_family = hl.literal({
            family_guid: [
                guid for guid, affected in affected_status.items() if affected == Individual.AFFECTED_STATUS_UNAFFECTED
            ] for family_guid, affected_status in family_individual_affected_status.items()
        })
        ch_ht = ch_ht.annotate(
            family_guids=ch_ht.family_guids.filter(lambda family_guid: unaffected_by_family[family_guid].all(
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
            self._ht = None

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

    def _format_results(self, ht):
        results = ht.annotate(
            genomeVersion=self._genome_version.replace('GRCh', ''),
            **{k: v(ht) for k, v in ANNOTATION_FIELDS.items()},
        )
        response_keys = ['genomeVersion', *CORE_FIELDS, *GENOTYPE_FIELDS, *ANNOTATION_FIELDS.keys()]
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
        if self._ht:
            self._ht = self._format_results(self._ht)
            if self._comp_het_ht:
                self._ht = self._ht.join(self._comp_het_ht, 'outer')
        else:
            self._ht = self._comp_het_ht

        if not self._ht:
            raise InvalidSearchException('Filters must be applied before search')

        total_results = self._ht.count()
        logger.info(f'Total hits: {total_results}')

        # TODO #2496: page, sort
        collected = self._ht.take(num_results)
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
        ht = super(VariantHailTableQuery, self)._load_table(data_source, intervals=None if exclude_intervals else intervals)
        if intervals and exclude_intervals:
            intervals = self._parse_intervals(intervals)
            ht = hl.filter_intervals(ht, intervals, keep=False)
        return ht


class GcnvHailTableQuery(BaseHailTableQuery):

    def _load_table(self, data_source, intervals=None, exclude_intervals=False):
        ht = super(GcnvHailTableQuery, self)._load_table(data_source)
        if intervals:
            intervals = self._parse_intervals(intervals)
            interval_filter = hl.array(intervals).all(lambda interval: not interval.overlaps(ht.interval)) \
                if exclude_intervals else hl.array(intervals).any(lambda interval: interval.overlaps(ht.interval))
            ht = ht.filter(interval_filter)
        return ht


class AllDataTypeHailTableQuery(BaseHailTableQuery):

    def _load_table(self, data_source, **kwargs):
        # TODO does not work, figure out multi-class inheritance
        ht = VariantHailTableQuery._load_table(data_source[Sample.DATASET_TYPE_VARIANT_CALLS], **kwargs)
        sv_ht = GcnvHailTableQuery._load_table(data_source[Sample.DATASET_TYPE_SV_CALLS], **kwargs)

        ht = ht.key_by(VARIANT_KEY_FIELD).join(sv_ht, how='outer')  # TODO key_by will break genotype joining
        transcript_struct_types = ht.sortedTranscriptConsequences.dtype.element_type
        sv_transcript_fields = ht.sortedTranscriptConsequences_1.dtype.element_type.keys()
        missing_transcript_fields = [k for k in TRANSCRIPT_FIELDS if k not in sv_transcript_fields]
        return ht.annotate(sortedTranscriptConsequences=hl.or_else(
            ht.sortedTranscriptConsequences.map(
                lambda t: t.select(*sv_transcript_fields, *missing_transcript_fields)),
            hl.array(ht.sortedTranscriptConsequences_1.map(
                lambda t: t.annotate(**{k: hl.missing(transcript_struct_types[k]) for k in missing_transcript_fields})))
        )).drop('sortedTranscriptConsequences_1')


class HailSearch(object):

    def __init__(self, families, previous_search_results=None, return_all_queried_families=False, user=None, sort=None):
        self.samples = Sample.objects.filter(
            is_active=True, individual__family__in=families,
        ).select_related('individual__family', 'individual__family__project')

        projects = {s.individual.family.project for s in self.samples}
        genome_version_projects = defaultdict(list)
        for p in projects:
            genome_version_projects[p.get_genome_version_display()].append(p.name)
        if len(genome_version_projects) > 1:
            project_builds = '; '.join(f'build [{", ".join(projects)}]' for build, projects in genome_version_projects.items())
            raise InvalidSearchException(
                f'Search is only enabled on a single genome build, requested the following project builds: {project_builds}')
        self._genome_version = list(genome_version_projects.keys())[0]

        self._user = user
        self._sort = sort
        self._return_all_queried_families = return_all_queried_families # In production: need to implement for reloading saved variants
        self.previous_search_results = previous_search_results or {}

    def _load_table(self, **kwargs):
        # TODO filter by searched dataset type
        data_sources_by_type = defaultdict(set)
        for s in self.samples:
            data_sources_by_type[s.dataset_type].add(s.elasticsearch_index)  # In production: should use a different model field
        multi_data_sources = next(
            (data_sources for data_sources in data_sources_by_type.values() if len(data_sources) > 1), None)
        if multi_data_sources:
            raise InvalidSearchException(
                f'Search is only enabled on a single data source, requested {", ".join(multi_data_sources)}')
        data_sources_by_type = {k: v.pop() for k, v in data_sources_by_type.items()}

        # TODO load correct data type
        self.samples = [s for s in self.samples if s.dataset_type == Sample.DATASET_TYPE_VARIANT_CALLS]
        data_source = data_sources_by_type[Sample.DATASET_TYPE_VARIANT_CALLS]
        query_cls = VariantHailTableQuery
        self._query_wrapper = query_cls(data_source, genome_version=self._genome_version, **kwargs)

    @classmethod
    def process_previous_results(cls, previous_search_results, page=1, num_results=100, load_all=False):
        # return EsSearch.process_previous_results(*args, **kwargs)
        # TODO #2496: re-enable caching, not helpful for initial development
        return None, {'page': page, 'num_results': num_results}

    def filter_variants(self, inheritance=None, genes=None, intervals=None, variant_ids=None, locus=None,
                        annotations_secondary=None, quality_filter=None, skip_genotype_filter=False, **kwargs):
        has_location_filter = genes or intervals
        if has_location_filter:
            self._filter_by_intervals(genes, intervals, locus.get('excludeLocations'))
        elif variant_ids:
            self.filter_by_variant_ids(variant_ids)
        else:
            self._load_table()

        quality_filter = quality_filter or {}
        self._query_wrapper.filter_variants(quality_filter=quality_filter, **kwargs)

        inheritance_mode = (inheritance or {}).get('mode')
        inheritance_filter = (inheritance or {}).get('filter') or {}
        if inheritance_filter.get('genotype'):
            inheritance_mode = None
        if not inheritance_mode and inheritance_filter and list(inheritance_filter.keys()) == ['affected']:
            raise InvalidSearchException('Inheritance must be specified if custom affected status is set')

        family_individual_affected_status = {}
        samples_by_family = defaultdict(dict)
        for s in self.samples:
            samples_by_family[s.individual.family.guid][s.sample_id] = s

        if inheritance:
            for family_guid, samples_by_id in samples_by_family.items():
                family_individual_affected_status[family_guid] = _get_family_affected_status(
                    samples_by_id, inheritance_filter)

            for family_guid, individual_affected_status in family_individual_affected_status.items():
                has_affected_samples = any(
                    aftd == Individual.AFFECTED_STATUS_AFFECTED for aftd in individual_affected_status.values()
                )
                if not has_affected_samples:
                    del samples_by_family[family_guid]

            if len(samples_by_family) < 1:
                raise InvalidSearchException(
                    'Inheritance based search is disabled in families with no data loaded for affected individuals')

        if inheritance_mode in {RECESSIVE, COMPOUND_HET}:
            if not has_location_filter and len(samples_by_family) > MAX_NO_LOCATION_COMP_HET_FAMILIES:
                raise InvalidSearchException(
                    'Location must be specified to search for compound heterozygous variants across many families')

            comp_het_only = inheritance_mode == COMPOUND_HET
            self._query_wrapper.filter_compound_hets(
                samples_by_family, family_individual_affected_status, annotations_secondary, quality_filter,
                keep_main_ht=not comp_het_only)
            if comp_het_only:
                return

        self._query_wrapper.filter_main_annotations()
        self._query_wrapper.annotate_filtered_genotypes(
            samples_by_family, family_individual_affected_status, inheritance_mode, inheritance_filter, quality_filter)

    def filter_by_variant_ids(self, variant_ids):
        # In production: support SV variant IDs?
        variant_ids = [EsSearch.parse_variant_id(variant_id) for variant_id in variant_ids]
        # TODO #2716: format chromosome for genome build
        intervals = [ f'[chr{chrom}:{pos}-{pos}]' for chrom, pos, _, _ in variant_ids]
        self._load_table(intervals=intervals)
        self._query_wrapper.filter_by_variant_ids(variant_ids)

    def _filter_by_intervals(self, genes, intervals, exclude_locations):
        parsed_intervals = None
        if genes or intervals:
            # TODO #2716: format chromosomes for genome build
            gene_coords = [
                {field: gene[f'{field}{self._genome_version.title()}'] for field in ['chrom', 'start', 'end']}
                for gene in (genes or {}).values()
            ]
            parsed_intervals = ['{chrom}:{start}-{end}'.format(**interval) for interval in intervals or []] + [
                'chr{chrom}:{start}-{end}'.format(**gene) for gene in gene_coords]

        self._load_table(intervals=parsed_intervals, exclude_intervals=exclude_locations)

    def search(self, page=1, num_results=100):
        hail_results, total_results = self._query_wrapper.search(page, num_results, self._sort)
        self.previous_search_results['total_results'] = total_results
        # TODO #2496 actually cache results
        return hail_results
