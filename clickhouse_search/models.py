from clickhouse_backend import models
from django.db.migrations import state
from django.db.models import options, ForeignKey, OneToOneField, Func, Manager, Q, CASCADE, PROTECT

from clickhouse_search.backend.engines import CollapsingMergeTree, EmbeddedRocksDB, Join
from clickhouse_search.backend.fields import NestedField, UInt64FieldDeltaCodecField, NamedTupleField
from clickhouse_search.backend.functions import ArrayFilter, GtStatsDictGet
from seqr.utils.search.constants import INHERITANCE_FILTERS, ANY_AFFECTED, AFFECTED, UNAFFECTED, MALE_SEXES, \
    X_LINKED_RECESSIVE, REF_REF, REF_ALT, ALT_ALT, HAS_ALT, HAS_REF, SPLICE_AI_FIELD, SCREEN_KEY, UTR_ANNOTATOR_KEY, \
    EXTENDED_SPLICE_KEY, MOTIF_FEATURES_KEY, REGULATORY_FEATURES_KEY, CLINVAR_KEY, HGMD_KEY, SV_ANNOTATION_TYPES, \
    EXTENDED_SPLICE_REGION_CONSEQUENCE, CLINVAR_PATH_RANGES, CLINVAR_PATH_SIGNIFICANCES, PATH_FREQ_OVERRIDE_CUTOFF, \
    HGMD_CLASS_FILTERS
from seqr.utils.xpos_utils import get_xpos, CHROMOSOMES
from settings import CLICKHOUSE_IN_MEMORY_DIR, CLICKHOUSE_DATA_DIR

options.DEFAULT_NAMES = (
    *options.DEFAULT_NAMES,
    'projection',
)
state.DEFAULT_NAMES = options.DEFAULT_NAMES


class ClickHouseRouter:
    """
    Adapted from https://github.com/jayvynl/django-clickhouse-backend/blob/v1.3.2/README.md#configuration
    """

    def __init__(self):
        self.route_model_names = set()
        for model in self._get_subclasses(models.ClickhouseModel):
            if model._meta.abstract:
                continue
            self.route_model_names.add(model._meta.label_lower)

    @staticmethod
    def _get_subclasses(class_):
        classes = class_.__subclasses__()

        index = 0
        while index < len(classes):
            classes.extend(classes[index].__subclasses__())
            index += 1

        return list(set(classes))

    def db_for_read(self, model, **hints):
        if model._meta.label_lower in self.route_model_names or hints.get('clickhouse'):
            return 'clickhouse'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.label_lower in self.route_model_names or hints.get('clickhouse'):
            return 'clickhouse'
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if f'{app_label}.{model_name}' in self.route_model_names  or hints.get('clickhouse'):
            return db == 'clickhouse'
        elif db == 'clickhouse':
            return False
        return None


class Projection(Func):

    def __init__(self, name, select='*', order_by=None):
        self.name = name
        self.select = select
        self.order_by = order_by


class BaseAnnotationsSnvIndel(models.ClickhouseModel):
    POPULATION_FIELDS = [
        ('exac', NamedTupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('an', models.UInt32Field()),
            ('filter_af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('hemi', models.UInt32Field()),
            ('het', models.UInt32Field()),
            ('hom', models.UInt32Field()),
        ])),
        ('gnomad_exomes', NamedTupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('an', models.UInt32Field()),
            ('filter_af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('hemi', models.UInt32Field()),
            ('hom', models.UInt32Field()),
        ])),
        ('gnomad_genomes', NamedTupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('an', models.UInt32Field()),
            ('filter_af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('hemi', models.UInt32Field()),
            ('hom', models.UInt32Field()),
        ])),
        ('topmed', NamedTupleField([
            ('ac', models.UInt32Field()),
            ('af', models.DecimalField(max_digits=9, decimal_places=5)),
            ('an', models.UInt32Field()),
            ('het', models.UInt32Field()),
            ('hom', models.UInt32Field()),
        ])),
    ]
    PREDICTION_FIELDS = [
        ('cadd', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('eigen', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('fathmm', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('gnomad_noncoding', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('mpc', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('mut_pred', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('mut_taster', models.Enum8Field(null=True, blank=True, return_int=False, choices=[(0, 'D'), (1, 'A'), (2, 'N'), (3, 'P')])),
        ('polyphen', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('primate_ai', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('revel', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('sift', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        (SPLICE_AI_FIELD, models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('splice_ai_consequence', models.Enum8Field(null=True, blank=True, return_int=False, choices=[(0, 'Acceptor gain'), (1, 'Acceptor loss'), (2, 'Donor gain'), (3, 'Donor loss'), (4, 'No consequence')])),
        ('vest', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
    ]
    HGMD_CLASSES = [(0, 'DM'), (1, 'DM?'), (2, 'DP'), (3, 'DFP'), (4, 'FP'), (5, 'R')]
    CONSEQUENCE_TERMS = [(1, 'transcript_ablation'), (2, 'splice_acceptor_variant'), (3, 'splice_donor_variant'), (4, 'stop_gained'), (5, 'frameshift_variant'), (6, 'stop_lost'), (7, 'start_lost'), (8, 'inframe_insertion'), (9, 'inframe_deletion'), (10, 'missense_variant'), (11, 'protein_altering_variant'), (12, 'splice_donor_5th_base_variant'), (13, 'splice_region_variant'), (14, 'splice_donor_region_variant'), (15, 'splice_polypyrimidine_tract_variant'), (16, 'incomplete_terminal_codon_variant'), (17, 'start_retained_variant'), (18, 'stop_retained_variant'), (19, 'synonymous_variant'), (20, 'coding_sequence_variant'), (21, 'mature_miRNA_variant'), (22, '5_prime_UTR_variant'), (23, '3_prime_UTR_variant'), (24, 'non_coding_transcript_exon_variant'), (25, 'intron_variant'), (26, 'NMD_transcript_variant'), (27, 'non_coding_transcript_variant'), (28, 'coding_transcript_variant'), (29, 'upstream_gene_variant'), (30, 'downstream_gene_variant'), (31, 'intergenic_variant'), (32, 'sequence_variant')]

    key = models.UInt32Field(primary_key=True)
    xpos = models.UInt64Field()
    chrom = models.Enum8Field(return_int=False, choices=[(i+1, chrom) for i, chrom in enumerate(CHROMOSOMES[:-1])])
    pos = models.UInt32Field()
    ref = models.StringField()
    alt = models.StringField()
    variant_id = models.StringField(db_column='variantId')
    rsid = models.StringField(null=True, blank=True)
    caid = models.StringField(db_column='CAID', null=True, blank=True)
    lifted_over_chrom = models.StringField(db_column='liftedOverChrom', low_cardinality=True, null=True, blank=True)
    lifted_over_pos = models.UInt32Field(db_column='liftedOverPos', null=True, blank=True)
    hgmd = NamedTupleField([
        ('accession', models.StringField(null=True, blank=True)),
        ('classification', models.Enum8Field(null=True, blank=True, return_int=False, choices=HGMD_CLASSES)),
    ], null_if_empty=True, rename_fields={'classification': 'class'})
    screen_region_type = models.Enum8Field(db_column='screenRegionType', null=True, blank=True, return_int=False, choices=[(0, 'CTCF-bound'), (1, 'CTCF-only'), (2, 'DNase-H3K4me3'), (3, 'PLS'), (4, 'dELS'), (5, 'pELS'), (6, 'DNase-only'), (7, 'low-DNase')])
    predictions = NamedTupleField(PREDICTION_FIELDS)
    populations = NamedTupleField(POPULATION_FIELDS)
    sorted_transcript_consequences = NestedField([
        ('alphamissensePathogenicity', models.DecimalField(null=True, blank=True, max_digits=9, decimal_places=5)),
        ('canonical', models.UInt8Field(null=True, blank=True)),
        ('consequenceTerms', models.ArrayField(models.Enum8Field(null=True, blank=True, return_int=False, choices=CONSEQUENCE_TERMS))),
        ('extendedIntronicSpliceRegionVariant', models.BoolField(null=True, blank=True)),
        ('fiveutrConsequence', models.Enum8Field(null=True, blank=True, return_int=False, choices=[(1, '5_prime_UTR_premature_start_codon_gain_variant'), (2, '5_prime_UTR_premature_start_codon_loss_variant'), (3, '5_prime_UTR_stop_codon_gain_variant'), (4, '5_prime_UTR_stop_codon_loss_variant'), (5, '5_prime_UTR_uORF_frameshift_variant')])),
        ('geneId', models.StringField(null=True, blank=True)),
    ], db_column='sortedTranscriptConsequences')
    sorted_motif_feature_consequences = NestedField([
        ('consequenceTerms', models.ArrayField(models.Enum8Field(null=True, blank=True, return_int=False, choices=[(0, 'TFBS_ablation'), (1, 'TFBS_amplification'), (2, 'TF_binding_site_variant'), (3, 'TFBS_fusion'), (4, 'TFBS_translocation')]))),
        ('motifFeatureId', models.StringField(null=True, blank=True)),
    ], db_column='sortedMotifFeatureConsequences', null_when_empty=True)
    sorted_regulatory_feature_consequences = NestedField([
        ('biotype', models.Enum8Field(null=True, blank=True, return_int=False, choices=[(0, 'enhancer'), (1, 'promoter'), (2, 'CTCF_binding_site'), (3, 'TF_binding_site'), (4, 'open_chromatin_region')])),
        ('consequenceTerms', models.ArrayField(models.Enum8Field(null=True, blank=True, return_int=False, choices=[(0, 'regulatory_region_ablation'), (1, 'regulatory_region_amplification'), (2, 'regulatory_region_variant'), (3, 'regulatory_region_fusion')]))),
        ('regulatoryFeatureId', models.StringField(null=True, blank=True)),
    ], db_column='sortedRegulatoryFeatureConsequences', null_when_empty=True)

    class Meta:
        abstract = True

class AnnotationsSnvIndel(BaseAnnotationsSnvIndel):

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/annotations_memory'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_IN_MEMORY_DIR}/GRCh38/SNV_INDEL/annotations', primary_key='key', flatten_nested=0)

# Future work: create an alias and manager to switch between disk/in-memory annotations
class AnnotationsDiskSnvIndel(BaseAnnotationsSnvIndel):

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/annotations_disk'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/SNV_INDEL/annotations', primary_key='key', flatten_nested=0)


class EntriesManager(Manager):
    GENOTYPE_LOOKUP = {
        REF_REF: (0,),
        REF_ALT: (1,),
        ALT_ALT: (2,),
        HAS_ALT: (0, '{field} > {value}'),
        HAS_REF: (2, '{field} < {value}'),
    }

    INHERITANCE_FILTERS = {
        **INHERITANCE_FILTERS,
        ANY_AFFECTED: {AFFECTED: HAS_ALT},
    }

    QUALITY_FILTERS = [('gq', 1), ('ab', 100, 'x.gt != 1')]

    POPULATIONS = {
        population: {subfield for subfield, _ in field.base_fields}
        for population, field in AnnotationsSnvIndel.POPULATION_FIELDS
    }
    IN_SILICO_SCORES = {score for score, _ in AnnotationsSnvIndel.PREDICTION_FIELDS}

    def search(self, sample_data, parsed_locus=None, **kwargs):
        parsed_locus = parsed_locus or {}
        entries = self._search_call_data(sample_data, **kwargs)
        entries = self._filter_location(entries, **parsed_locus)
        entries = entries.annotate(seqrPop=GtStatsDictGet('key'))
        entries = self._filter_frequency(entries, **kwargs)
        entries = self._filter_in_silico(entries, **kwargs)
        entries = self._filter_annotations(entries, **parsed_locus, **kwargs)
        return entries

    def _search_call_data(self, sample_data, inheritance_mode=None, inheritance_filter=None, qualityFilter=None, pathogenicity=None, **kwargs):
       if len(sample_data) > 1:
           raise NotImplementedError('Clickhouse search not implemented for multiple families or sample types')

       entries = self.filter(
           project_guid=sample_data[0]['project_guid'],
           family_guid=sample_data[0]['family_guid'],
       )

       quality_filter = qualityFilter or {}
       if quality_filter.get('vcf_filter'):
           entries = entries.filter(filters__len=0)

       individual_genotype_filter = (inheritance_filter or {}).get('genotype')
       custom_affected = (inheritance_filter or {}).get('affected') or {}
       if not (inheritance_mode or individual_genotype_filter or quality_filter):
           return entries

       clinvar_override_q = self._clinvar_path_q(pathogenicity)

       for sample in sample_data[0]['samples']:
           affected = custom_affected.get(sample['individual_guid']) or sample['affected']
           sample_inheritance_filter = self._sample_genotype_filter(sample, affected, inheritance_mode, individual_genotype_filter)
           sample_quality_filter = self._sample_quality_filter(affected, quality_filter)
           if not (sample_inheritance_filter or sample_quality_filter):
               continue
           sample_inheritance_filter['sampleId'] = (f"'{sample['sample_id']}'",)
           sample_q = Q(calls__array_exists={**sample_inheritance_filter, **sample_quality_filter})
           if clinvar_override_q and sample_quality_filter:
               sample_q |= clinvar_override_q & Q(calls__array_exists=sample_inheritance_filter)

           entries = entries.filter(sample_q)

       return entries

    @classmethod
    def _sample_genotype_filter(cls, sample, affected, inheritance_mode, individual_genotype_filter):
        sample_filter = {}
        genotype = None
        if individual_genotype_filter:
            genotype = individual_genotype_filter.get(sample['individual_guid'])
        elif inheritance_mode:
            genotype = cls.INHERITANCE_FILTERS[inheritance_mode].get(affected)
            if (inheritance_mode == X_LINKED_RECESSIVE and affected == UNAFFECTED and sample['sex'] in MALE_SEXES):
                genotype = REF_REF
        if genotype:
            sample_filter['gt'] = cls.GENOTYPE_LOOKUP[genotype]
        return sample_filter

    @classmethod
    def _sample_quality_filter(cls, affected, quality_filter):
        sample_filter = {}
        if quality_filter.get('affected_only') and affected != AFFECTED:
            return sample_filter

        for field, scale, *filters in cls.QUALITY_FILTERS:
            value = quality_filter.get(f'min_{field}')
            if value:
                or_filters = ['isNull({field})', '{field} >= {value}'] + filters
                sample_filter[field] = (value / scale, f'or({", ".join(or_filters)})')

        return sample_filter

    @classmethod
    def _filter_location(cls, entries, exclude_intervals=False, intervals=None, variant_ids=None, rs_ids=None, **kwargs):
        if variant_ids:
            entries = entries.filter(
                key__variant_id__in=[f'{chrom}-{pos}-{ref}-{alt}' for chrom, pos, ref, alt in variant_ids]
            )
            # although technically redundant, the interval query is applied to the entries table before join and reduces the join size,
            # while the variant_id filter is applied to the annotation table after the join
            intervals = [(chrom, pos, pos) for chrom, pos, _, _ in variant_ids]

        if intervals:
            interval_q = cls._interval_query(*intervals[0])
            for interval in intervals[1:]:
                interval_q |= cls._interval_query(*interval)
            filter_func = entries.exclude if exclude_intervals else entries.filter
            entries = filter_func(interval_q)

        if rs_ids:
            entries = entries.filter(key__rsid__in=rs_ids)

        return entries

    @staticmethod
    def _interval_query(chrom, start, end):
        return Q(xpos__range=(get_xpos(chrom, start), get_xpos(chrom, end)))

    @classmethod
    def _filter_frequency(cls, entries, freqs=None, pathogenicity=None, **kwargs):
        frequencies =  freqs or {}

        gnomad_filter = frequencies.get('gnomad_genomes') or {}
        if (gnomad_filter.get('af') or 1) <= 0.05 or any(gnomad_filter.get(field) is not None for field in ['ac', 'hh']):
            entries = entries.filter(is_gnomad_gt_5_percent=False)

        clinvar_override_q = cls._clinvar_path_q(pathogenicity)

        for population, pop_filter in frequencies.items():
            pop_subfields = cls.POPULATIONS.get(population)
            if not pop_subfields:
                continue

            if pop_filter.get('af') is not None and pop_filter['af'] < 1:
                af_field = next(field for field in ['filter_af', 'af'] if field in pop_subfields)
                if af_field:
                    af_q = Q(**{
                        f'key__populations__{population}__{af_field}__lte': pop_filter['af'],
                    })
                    if clinvar_override_q and pop_filter['af'] < PATH_FREQ_OVERRIDE_CUTOFF:
                        af_q |= clinvar_override_q
                    entries = entries.filter(af_q)
            elif pop_filter.get('ac') is not None:
                entries = entries.filter(**{f'key__populations__{population}__ac__lte': pop_filter['ac']})

            if pop_filter.get('hh') is not None:
                for subfield in ['hom', 'hemi']:
                    if subfield not in pop_subfields:
                        continue
                    hh_q = Q(**{
                        f'key__populations__{population}__{subfield}__lte': pop_filter['hh'],
                    })
                    if clinvar_override_q:
                        hh_q |= clinvar_override_q
                    entries = entries.filter(hh_q)

        if frequencies.get('callset'):
            entries = cls._filter_seqr_frequency(entries, **frequencies['callset'])

        return entries

    @classmethod
    def _filter_seqr_frequency(cls, entries, ac=None, hh=None, **kwargs):
        if ac is not None:
            entries = entries.filter(seqrPop__0__lte=ac)
        if hh is not None:
            entries = entries.filter(seqrPop__1__lte=hh)
        return entries

    @classmethod
    def _filter_in_silico(cls, entries, in_silico=None, **kwargs):
        in_silico_filters = {
            score: value for score, value in (in_silico or {}).items() if score in cls.IN_SILICO_SCORES and value
        }
        if not in_silico_filters:
            return entries

        in_silico_q = None
        for score, value in in_silico_filters.items():
            score_q = cls._get_in_silico_score_q(score, value)
            if in_silico_q is None:
                in_silico_q = score_q
            else:
                in_silico_q |= score_q

        if not in_silico.get('requireScore', False):
            in_silico_q |= Q(**{f'key__predictions__{score}__isnull': True for score in in_silico_filters.keys()})

        return entries.filter(in_silico_q)

    @staticmethod
    def _get_in_silico_score_q(score, value):
        score_column = f'key__predictions__{score}'
        try:
            return Q(**{f'{score_column}__gte': float(value)})
        except ValueError:
            return Q(**{score_column: value})

    @classmethod
    def _filter_annotations(cls, entries, annotations=None, pathogenicity=None, exclude=None, gene_ids=None, **kwargs):
        if gene_ids:
            entries = entries.annotate(gene_consequences=ArrayFilter('key__sorted_transcript_consequences', conditions=[{
                'geneId': (gene_ids, 'has({value}, {field})'),
            }]))
            entries = entries.filter(gene_consequences__not_empty=True)

        filter_qs, transcript_filters = cls._parse_annotation_filters(annotations) if annotations else ([], [])
        if transcript_filters:
            consequence_field = 'gene_consequences' if gene_ids else 'key__sorted_transcript_consequences'
            entries = entries.annotate(
                filtered_transcript_consequences=ArrayFilter(consequence_field, conditions=transcript_filters),
            )
            filter_qs.append(Q(filtered_transcript_consequences__not_empty=True))

        hgmd = (pathogenicity or {}).get(HGMD_KEY)
        if hgmd:
            filter_qs.append(cls._hgmd_filter_q(hgmd))

        has_clinvar_inner_join = False
        clinvar = (pathogenicity or {}).get(CLINVAR_KEY)
        if clinvar:
            has_clinvar_inner_join = not filter_qs
            filter_qs.append(cls._clinvar_filter_q(clinvar))

        exclude_clinvar = (exclude or {}).get('clinvar')
        if exclude_clinvar:
            entries = entries.exclude(cls._clinvar_filter_q(exclude_clinvar))

        if not filter_qs:
            return entries

        filter_q = filter_qs[0]
        for q in filter_qs[1:]:
            filter_q |= q
        entries = entries.filter(filter_q)

        if has_clinvar_inner_join:
            # If clinvar is filtered on with no OR clauses, django optimizes the query to use an INNER JOIN.
            # However, the clickhouse Join Table can only be used with a LEFT OUTER JOIN, so we explicitly "promote" the
            # join type to an outer join. The filters remain unchanged, so no other query updates are needed
            entries.query.promote_joins([Clinvar._meta.db_table])

        return entries

    @classmethod
    def _parse_annotation_filters(cls, annotations):
        filter_qs = []
        allowed_consequences = []
        transcript_filters = []
        for field, value in annotations.items():
            if field == UTR_ANNOTATOR_KEY:
                transcript_filters.append({'fiveutrConsequence': (value, 'hasAny({value}, [{field}])')})
            elif field == EXTENDED_SPLICE_KEY:
                if EXTENDED_SPLICE_REGION_CONSEQUENCE in value:
                    transcript_filters.append({'extendedIntronicSpliceRegionVariant': (1, '{field} = {value}')})
            elif field in [MOTIF_FEATURES_KEY, REGULATORY_FEATURES_KEY]:
                filter_qs.append(Q(**{f'key__sorted_{field}_consequences__array_exists': {
                    'consequenceTerms': (value, 'hasAny({value}, {field})'),
                }}))
            elif field == SPLICE_AI_FIELD:
                filter_qs.append(cls._get_in_silico_score_q(SPLICE_AI_FIELD, value))
            elif field == SCREEN_KEY:
                filter_qs.append(Q(key__screen_region_type__in=value))
            elif field not in SV_ANNOTATION_TYPES:
                allowed_consequences += value

        non_canonical_consequences = [c for c in allowed_consequences if not c.endswith('__canonical')]
        if non_canonical_consequences:
            transcript_filters.append(cls._consequence_term_filter(non_canonical_consequences))

        canonical_consequences = [
            c.replace('__canonical', '') for c in allowed_consequences if c.endswith('__canonical')
        ]
        if canonical_consequences:
            transcript_filters.append(
                cls._consequence_term_filter(canonical_consequences, canonical=(0, '{field} > {value}')),
            )

        return filter_qs, transcript_filters

    @staticmethod
    def _consequence_term_filter(consequences, **kwargs):
        return {'consequenceTerms': (consequences, 'hasAny({value}, {field})'), **kwargs}

    @staticmethod
    def _hgmd_filter_q(hgmd):
        min_class = next((class_name for value, class_name in HGMD_CLASS_FILTERS if value in hgmd), None)
        max_class = next((class_name for value, class_name in reversed(HGMD_CLASS_FILTERS) if value in hgmd), None)
        if 'hgmd_other' in hgmd:
            min_class = min_class or 'DP'
            max_class = None
        if min_class == max_class:
            return Q(key__hgmd__classification=min_class)
        elif min_class and max_class:
            return Q(key__hgmd__classification__range=(min_class, max_class))
        return Q(key__hgmd__classification__gt=min_class)

    @staticmethod
    def _clinvar_filter_q(clinvar_filters):
        ranges = [[None, None]]
        for path_filter, start, end in CLINVAR_PATH_RANGES:
            if path_filter in clinvar_filters:
                ranges[-1][1] = end
                if ranges[-1][0] is None:
                    ranges[-1][0] = start
            elif ranges[-1] != [None, None]:
                ranges.append([None, None])
        ranges = [r for r in ranges if r[0] is not None]

        clinvar_q = Q(key__clinvar__pathogenicity__range=ranges[0])
        for path_range in ranges[1:]:
            clinvar_q |= Q(key__clinvar__pathogenicity__range=path_range)
        return clinvar_q

    @classmethod
    def _clinvar_path_q(cls, pathogenicity):
        clinvar_path_filters = [
            f for f in (pathogenicity or {}).get(CLINVAR_KEY) or [] if f in CLINVAR_PATH_SIGNIFICANCES
        ]
        return cls._clinvar_filter_q(clinvar_path_filters) if clinvar_path_filters else None


class EntriesSnvIndel(models.ClickhouseModel):
    CALL_FIELDS = [
        ('sampleId', models.StringField()),
        ('gt', models.Enum8Field(null=True, blank=True, choices=[(0, 'REF'), (1, 'HET'), (2, 'HOM')])),
        ('gq', models.UInt8Field(null=True, blank=True)),
        ('ab', models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)),
        ('dp', models.UInt16Field(null=True, blank=True)),
    ]

    objects = EntriesManager()

    # primary_key is not enforced by clickhouse, but setting it here prevents django adding an id column
    key = ForeignKey('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)
    project_guid = models.StringField(low_cardinality=True)
    family_guid = models.StringField()
    sample_type = models.Enum8Field(choices=[(1, 'WES'), (2, 'WGS')])
    xpos = UInt64FieldDeltaCodecField()
    is_gnomad_gt_5_percent = models.BoolField()
    filters = models.ArrayField(models.StringField(low_cardinality=True))
    calls = models.ArrayField(NamedTupleField(CALL_FIELDS))
    sign = models.Int8Field()

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/entries'
        engine = CollapsingMergeTree(
            'sign',
            order_by=('project_guid', 'family_guid', 'is_gnomad_gt_5_percent', 'key'),
            partition_by='project_guid',
            deduplicate_merge_projection_mode='rebuild',
            index_granularity=8192,
        )
        projection = Projection('xpos_projection', order_by='xpos, is_gnomad_gt_5_percent')

    def _save_table(
        self,
        raw=False,
        cls=None,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        # loaddata attempts to run an ALTER TABLE to update existing rows, but since primary keys can not be altered
        # this command fails so need to use the force_insert flag to run an INSERT instead
        return super()._save_table(
            raw=raw, cls=cls, force_insert=True, force_update=force_update, using=using, update_fields=update_fields,
        )


class TranscriptsSnvIndel(models.ClickhouseModel):
    key = OneToOneField('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=CASCADE)
    transcripts = NestedField([
        ('alphamissense', NamedTupleField([
            ('pathogenicity', models.DecimalField(null=True, blank=True, max_digits=9, decimal_places=5)),
        ])),
        ('aminoAcids', models.StringField(null=True, blank=True)),
        ('biotype', models.StringField(null=True, blank=True)),
        ('canonical', models.UInt8Field(null=True, blank=True)),
        ('codons', models.StringField(null=True, blank=True)),
        ('consequenceTerms', models.ArrayField(models.StringField())),
        ('exon', NamedTupleField([
            ('index', models.Int32Field(null=True, blank=True)),
            ('total', models.Int32Field(null=True, blank=True)),
        ], null_if_empty=True)),
        ('geneId', models.StringField(null=True, blank=True)),
        ('hgvsc', models.StringField(null=True, blank=True)),
        ('hgvsp', models.StringField(null=True, blank=True)),
        ('intron', NamedTupleField([
            ('index', models.Int32Field(null=True, blank=True)),
            ('total', models.Int32Field(null=True, blank=True)),
        ], null_if_empty=True)),
        ('loftee', NamedTupleField([
            ('isLofNagnag', models.BoolField(null=True, blank=True)),
            ('lofFilters', models.ArrayField(models.StringField(null=True, blank=True))),
        ], null_empty_arrays=True)),
        ('majorConsequence', models.StringField(null=True, blank=True)),
        ('manePlusClinical', models.StringField(null=True, blank=True)),
        ('maneSelect', models.StringField(null=True, blank=True)),
        ('refseqTranscriptId', models.StringField(null=True, blank=True)),
        ('spliceregion', NamedTupleField([
            ('extended_intronic_splice_region_variant', models.BoolField(null=True, blank=True)),
        ])),
        ('transcriptId', models.StringField()),
        ('transcriptRank', models.UInt8Field()),
        ('utrannotator', NamedTupleField([
            ('existingInframeOorfs', models.Int32Field(null=True, blank=True)),
            ('existingOutofframeOorfs', models.Int32Field(null=True, blank=True)),
            ('existingUorfs', models.Int32Field(null=True, blank=True)),
            ('fiveutrAnnotation', NamedTupleField([
                ('AltStop', models.StringField(null=True, blank=True)),
                ('AltStopDistanceToCDS', models.Int32Field(null=True, blank=True)),
                ('CapDistanceToStart', models.Int32Field(null=True, blank=True)),
                ('DistanceToCDS', models.Int32Field(null=True, blank=True)),
                ('DistanceToStop', models.Int32Field(null=True, blank=True)),
                ('Evidence', models.BoolField(null=True, blank=True)),
                ('FrameWithCDS', models.StringField(null=True, blank=True)),
                ('KozakContext', models.StringField(null=True, blank=True)),
                ('KozakStrength', models.StringField(null=True, blank=True)),
                ('StartDistanceToCDS', models.Int32Field(null=True, blank=True)),
                ('alt_type', models.StringField(null=True, blank=True)),
                ('alt_type_length', models.Int32Field(null=True, blank=True)),
                ('newSTOPDistanceToCDS', models.Int32Field(null=True, blank=True)),
                ('ref_StartDistanceToCDS', models.Int32Field(null=True, blank=True)),
                ('ref_type', models.StringField(null=True, blank=True)),
                ('ref_type_length', models.Int32Field(null=True, blank=True)),
                ('type', models.StringField(null=True, blank=True)),
            ], null_if_empty=True)),
            ('fiveutrConsequence', models.StringField(null=True, blank=True)),
        ])),
    ], group_by_key='geneId')

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/transcripts'
        engine = EmbeddedRocksDB(0, f'{CLICKHOUSE_DATA_DIR}/GRCh38/SNV_INDEL/transcripts', primary_key='key', flatten_nested=0)


class Clinvar(models.ClickhouseModel):

    PATHOGENICITY_CHOICES = list(enumerate([
        'Pathogenic', 'Pathogenic/Likely_pathogenic', 'Pathogenic/Likely_pathogenic/Established_risk_allele',
        'Pathogenic/Likely_pathogenic/Likely_risk_allele', 'Pathogenic/Likely_risk_allele', 'Likely_pathogenic', 'Likely_pathogenic/Likely_risk_allele',
        'Established_risk_allele', 'Likely_risk_allele', 'Conflicting_classifications_of_pathogenicity',
        'Uncertain_risk_allele', 'Uncertain_significance/Uncertain_risk_allele', 'Uncertain_significance',
        'No_pathogenic_assertion', 'Likely_benign', 'Benign/Likely_benign', 'Benign'
    ]))

    key = OneToOneField('AnnotationsSnvIndel', db_column='key', primary_key=True, on_delete=PROTECT)
    allele_id = models.UInt32Field(db_column='alleleId', null=True, blank=True)
    conflicting_pathogenicities = NestedField([
        ('count', models.UInt16Field()),
        ('pathogenicity', models.Enum8Field(choices=PATHOGENICITY_CHOICES, return_int=False)),
    ], db_column='conflictingPathogenicities', null_when_empty=True)
    gold_stars = models.UInt8Field(db_column='goldStars', null=True, blank=True)
    submitters = models.ArrayField(models.StringField())
    conditions = models.ArrayField(models.StringField())
    assertions = models.ArrayField(models.Enum8Field(choices=[(0, 'Affects'), (1, 'association'), (2, 'association_not_found'), (3, 'confers_sensitivity'), (4, 'drug_response'), (5, 'low_penetrance'), (6, 'not_provided'), (7, 'other'), (8, 'protective'), (9, 'risk_factor'), (10, 'no_classification_for_the_single_variant'), (11, 'no_classifications_from_unflagged_records')], return_int=False))
    pathogenicity = models.Enum8Field(choices=PATHOGENICITY_CHOICES, return_int=False)

    class Meta:
        db_table = 'GRCh38/SNV_INDEL/clinvar'
        engine = Join('ALL', 'LEFT', 'key', join_use_nulls=1, flatten_nested=0)

    def _save_table(
        self,
        raw=False,
        cls=None,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        # loaddata attempts to run an ALTER TABLE to update existing rows, but since JOIN tables can not be altered
        # this command fails so need to use the force_insert flag to run an INSERT instead
        return super()._save_table(
            raw=raw, cls=cls, force_insert=True, force_update=force_update, using=using, update_fields=update_fields,
        )
