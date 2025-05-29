from clickhouse_backend import models
from collections import OrderedDict
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F, Value
from django.db.models.functions import JSONObject

from clickhouse_search.backend.fields import NestedField, NamedTupleField
from clickhouse_search.backend.functions import Array, ArrayMap, GtStatsDictGet, Tuple, TupleConcat
from clickhouse_search.models import EntriesSnvIndel, AnnotationsSnvIndel, TranscriptsSnvIndel, Clinvar
from reference_data.models import GeneConstraint, Omim, GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import PhenotypePrioritization, Sample
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.search.constants import MAX_VARIANTS, XPOS_SORT_KEY, PATHOGENICTY_SORT_KEY, PATHOGENICTY_HGMD_SORT_KEY, \
    PRIORITIZED_GENE_SORT
from settings import CLICKHOUSE_SERVICE_HOSTNAME

logger = SeqrLogger(__name__)

CORE_ENTRIES_FIELDS = ['key', 'xpos']

GT_STATS_DICT_FIELDS = OrderedDict({
    'ac': models.UInt32Field(),
    'hom': models.UInt32Field(),
})
GT_STATS_DICT_ATTRS_WES = [f"'{field}_wes'" for field in GT_STATS_DICT_FIELDS.keys()]
GT_STATS_DICT_ATTRS_WGS = [f"'{field}_wgs'" for field in GT_STATS_DICT_FIELDS.keys()]
SEQR_POPULATION_KEY = 'seqrPop'

ANNOTATION_VALUES = {
    field.db_column or field.name: F(f'key__{field.name}') for field in AnnotationsSnvIndel._meta.local_fields
    if field.name not in CORE_ENTRIES_FIELDS
}
ANNOTATION_VALUES['populations'] = TupleConcat(
    ANNOTATION_VALUES['populations'], Tuple(SEQR_POPULATION_KEY),
    output_field=NamedTupleField([
        *AnnotationsSnvIndel.POPULATION_FIELDS,
        ('seqr', NamedTupleField(list(GT_STATS_DICT_FIELDS.items()))),
    ]),
)

CLINVAR_FIELDS = OrderedDict({
    f'key__clinvar__{field.name}': (field.db_column or field.name, field)
    for field in Clinvar._meta.local_fields if field.name not in CORE_ENTRIES_FIELDS
})

GENOTYPE_FIELDS = OrderedDict({
    'family_guid': ('familyGuid', models.StringField()),
    'sample_type': ('sampleType', models.StringField()),
    'filters': ('filters', models.ArrayField(models.StringField())),
    'x.gt::Nullable(Int8)': ('numAlt', models.Int8Field(null=True, blank=True)),
    **{f'x.{column[0]}': column for column in EntriesSnvIndel.CALL_FIELDS if column[0] != 'gt'}
})

TRANSCRIPT_CONSEQUENCES_FIELD = 'sortedTranscriptConsequences'
SELECTED_GENE_FIELD = 'selectedGeneId'
SELECTED_TRANSCRIPT_FIELD = 'selectedTranscript'
SELECTED_CONSEQUENCE_VALUES = {
    'gene_consequences': {SELECTED_GENE_FIELD: F('gene_consequences__0__geneId')},
    'filtered_transcript_consequences': {SELECTED_TRANSCRIPT_FIELD: F('filtered_transcript_consequences__0')},
}


def clickhouse_backend_enabled():
    return bool(CLICKHOUSE_SERVICE_HOSTNAME)


def get_clickhouse_variants(samples, search, user, previous_search_results, genome_version,page=1, num_results=100, sort=None, **kwargs):
    if genome_version != GENOME_VERSION_GRCh38:
        raise NotImplementedError('Clickhouse search not implemented for genome version other than GRCh38')

    sample_data = _get_sample_data(samples)
    logger.info(f'Loading {Sample.DATASET_TYPE_VARIANT_CALLS} data for {len(sample_data)} families', user)

    entries = EntriesSnvIndel.objects.search(sample_data, **search)

    consequence_values = {}
    for field, value in SELECTED_CONSEQUENCE_VALUES.items():
        if field in entries.query.annotations:
            consequence_values.update(value)

    results = entries.annotate(**{
        SEQR_POPULATION_KEY: GtStatsDictGet(
            'key',
            dict_attrs_1=f"({', '.join(GT_STATS_DICT_ATTRS_WES)})",
            dict_attrs_2=f"({', '.join(GT_STATS_DICT_ATTRS_WGS)})",
        )
    }).values(
        *CORE_ENTRIES_FIELDS,
        familyGuids=Array('family_guid'),
        genotypes=ArrayMap(
            'calls',
            mapped_expression=f"tuple({_get_sample_map_expression(sample_data)}[x.sampleId], {', '.join(GENOTYPE_FIELDS.keys())})",
            output_field=NestedField([('individualGuid', models.StringField()), *GENOTYPE_FIELDS.values()], group_by_key='individualGuid', flatten_groups=True)
        ),
        clinvar=Tuple(*CLINVAR_FIELDS.keys(), output_field=NamedTupleField(list(CLINVAR_FIELDS.values()), null_if_empty=True, null_empty_arrays=True)),
        genomeVersion=Value(genome_version),
        liftedOverGenomeVersion=Value(_liftover_genome_version(genome_version)),
        **ANNOTATION_VALUES,
        **consequence_values,
    )
    results = results[:MAX_VARIANTS+1]

    sorted_results = sorted(results, key=_get_sort_key(sort, _get_sort_gene_metadata(sort, results)))
    total_results = len(sorted_results)
    previous_search_results.update({'all_results': sorted_results, 'total_results': total_results})

    logger.info(f'Total results: {total_results}', user)

    return format_clickhouse_results(sorted_results[(page-1)*num_results:page*num_results])


def format_clickhouse_results(results, **kwargs):
    keys_with_transcripts = [variant['key'] for variant in results if variant[TRANSCRIPT_CONSEQUENCES_FIELD]]
    transcripts_by_key = dict(
        TranscriptsSnvIndel.objects.filter(key__in=keys_with_transcripts).values_list('key', 'transcripts')
    )

    formatted_results = []
    for variant in results:
        transcripts = transcripts_by_key.get(variant['key'], {})
        formatted_variant = {
            **variant,
            'transcripts': transcripts,
        }
        # pop sortedTranscriptConsequences from the formatted result and not the original result to ensure the full value is cached properly
        sorted_minimal_transcripts = formatted_variant.pop(TRANSCRIPT_CONSEQUENCES_FIELD)
        selected_gene_id = formatted_variant.pop(SELECTED_GENE_FIELD, None)
        selected_transcript = formatted_variant.pop(SELECTED_TRANSCRIPT_FIELD, None)
        main_transcript_id = None
        selected_main_transcript_id = None
        if sorted_minimal_transcripts:
            main_transcript_id = next(
                t['transcriptId'] for t in transcripts[sorted_minimal_transcripts[0]['geneId']]
                if t['transcriptRank'] == 0
            )
        if selected_transcript:
            selected_main_transcript_id = next(
                t['transcriptId'] for t in transcripts[selected_transcript['geneId']]
                if _is_matched_minimal_transcript(t, selected_transcript)
            )
        elif selected_gene_id:
            selected_main_transcript_id = transcripts[selected_gene_id][0]['transcriptId']
        formatted_results.append({
            **formatted_variant,
            'mainTranscriptId': main_transcript_id,
            'selectedMainTranscriptId': None if selected_main_transcript_id == main_transcript_id else selected_main_transcript_id,
        })

    return formatted_results


def _is_matched_minimal_transcript(transcript, minimal_transcript):
    return (all(transcript[field] == minimal_transcript[field] for field in ['canonical','consequenceTerms'])
     and transcript['utrannotator'].get('fiveutrConsequence') == minimal_transcript['fiveutrConsequence']
     and transcript['spliceregion'].get('extended_intronic_splice_region_variant') == minimal_transcript['extendedIntronicSpliceRegionVariant'])



def _get_sample_data(samples):
    samples = samples.filter(dataset_type=Sample.DATASET_TYPE_VARIANT_CALLS)
    if not samples:
        raise NotImplementedError('Clickhouse search not implemented for other data types')

    return samples.values(
        'sample_type', family_guid=F('individual__family__guid'), project_guid=F('individual__family__project__guid'),
    ).annotate(samples=ArrayAgg(JSONObject(affected='individual__affected', sex='individual__sex', sample_id='sample_id', individual_guid=F('individual__guid'))))


def _get_sample_map_expression(sample_data):
    sample_map = [
        f"'{s['sample_id']}', '{s['individual_guid']}'"
        for data in sample_data for s in data['samples']
    ]
    return f"map({', '.join(sample_map)})"


def _liftover_genome_version(genome_version):
    return GENOME_VERSION_GRCh37 if genome_version == GENOME_VERSION_GRCh38 else GENOME_VERSION_GRCh38


OMIM_SORT = 'in_omim'
GENE_SORTS = {
    'constraint': lambda gene_ids: {
        agg['gene__gene_id']: agg['mis_z_rank'] + agg['pLI_rank'] for agg in
        GeneConstraint.objects.filter(gene__gene_id__in=gene_ids).values('gene__gene_id', 'mis_z_rank', 'pLI_rank')
    },
    OMIM_SORT: lambda gene_ids: set(Omim.objects.filter(
        gene__gene_id__in=gene_ids, phenotype_mim_number__isnull=False,
    ).values_list('gene__gene_id', flat=True)),
    # PRIORITIZED_GENE_SORT: lambda gene_ids: {
    #     agg['gene_id']: agg['min_rank'] for agg in PhenotypePrioritization.objects.filter(
    #         gene__gene_id__in=gene_ids, individual__family_id=samples[0].individual.family_id, rank__lte=100,
    #     ).values('gene_id').annotate(min_rank=Min('rank'))
    # },
}

def _get_sort_gene_metadata(sort, results):
    get_metadata = GENE_SORTS.get(sort)
    if not get_metadata:
        return None

    gene_ids = set()
    for result in results:
        gene_ids.update([t['geneId'] for t in result.get(TRANSCRIPT_CONSEQUENCES_FIELD, [])])
    return get_metadata(gene_ids)


def _subfield_sort(*fields, rank_lookup=None, default=1000, reverse=False):
    def _sort(item):
        for field in fields:
            item = (item or {}).get(field)
        if rank_lookup:
            item = rank_lookup.get(item)
        value = default if item is None else item
        return value if not reverse else -value
    return [_sort]


CLINVAR_RANK_LOOKUP = {path: rank for rank, path in Clinvar.PATHOGENICITY_CHOICES}
HGMD_RANK_LOOKUP = {class_: rank for rank, class_ in AnnotationsSnvIndel.HGMD_CLASSES}
ABSENT_CLINVAR_SORT_OFFSET = 12.5
CONSEQUENCE_RANK_LOOKUP = {csq: rank for rank, csq in AnnotationsSnvIndel.CONSEQUENCE_TERMS}
PREDICTION_SORTS = {'cadd', 'revel', 'splice_ai', 'eigen', 'mpc', 'primate_ai'}
CLINVAR_SORT =  _subfield_sort(
    'clinvar', 'pathogenicity', rank_lookup=CLINVAR_RANK_LOOKUP, default=ABSENT_CLINVAR_SORT_OFFSET,
)
SORT_EXPRESSIONS = {
    'alphamissense': [
        lambda x: -max(t.get('alphamissensePathogenicity') or 0 for t in x[TRANSCRIPT_CONSEQUENCES_FIELD]) if x[TRANSCRIPT_CONSEQUENCES_FIELD] else 0,
    ] + _subfield_sort(SELECTED_TRANSCRIPT_FIELD, 'alphamissensePathogenicity', reverse=True, default=0),
    'callset_af': _subfield_sort('populations', 'seqr', 'ac'),
    'family_guid': [],
    'gnomad': _subfield_sort('populations', 'gnomad_genomes', 'af'),
    'gnomad_exomes': _subfield_sort('populations', 'gnomad_exomes', 'af'),
    PATHOGENICTY_SORT_KEY: CLINVAR_SORT,
    PATHOGENICTY_HGMD_SORT_KEY: CLINVAR_SORT + _subfield_sort('hgmd', 'class', rank_lookup=HGMD_RANK_LOOKUP),
    'protein_consequence': [
        lambda x: CONSEQUENCE_RANK_LOOKUP[x[TRANSCRIPT_CONSEQUENCES_FIELD][0]['consequenceTerms'][0]] if x[TRANSCRIPT_CONSEQUENCES_FIELD] else 1000,
        lambda x: CONSEQUENCE_RANK_LOOKUP[x[SELECTED_TRANSCRIPT_FIELD]['consequenceTerms'][0]] if x.get(SELECTED_TRANSCRIPT_FIELD) else 1000,
    ],
    **{sort: _subfield_sort('predictions', sort, reverse=True, default=-1) for sort in PREDICTION_SORTS},
}

def _get_sort_key(sort, gene_metadata):
    sort_expressions = SORT_EXPRESSIONS.get(sort, [])

    if sort == OMIM_SORT:
        sort_expressions = [
            lambda x: 0 if ((x.get(SELECTED_TRANSCRIPT_FIELD) or {}).get('geneId') or x.get(SELECTED_GENE_FIELD)) in gene_metadata else 1,
            lambda x: -len(set(t['geneId'] for t in x.get(TRANSCRIPT_CONSEQUENCES_FIELD, []) if t['geneId'] in gene_metadata)),
        ]
    elif gene_metadata:
        sort_expressions = [
            lambda x: gene_metadata.get((x.get(SELECTED_TRANSCRIPT_FIELD) or {}).get('geneId') or x.get(SELECTED_GENE_FIELD), 1000),
            lambda x: min([gene_metadata[t['geneId']] for t in x.get(TRANSCRIPT_CONSEQUENCES_FIELD, []) if t['geneId'] in gene_metadata] or [1e10]),
        ]

    return lambda x: tuple(expr(x) for expr in [*sort_expressions, lambda x: x[XPOS_SORT_KEY]])
