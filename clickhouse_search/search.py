from clickhouse_backend import models
from collections import OrderedDict
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F, Value
from django.db.models.functions import JSONObject

from clickhouse_search.backend.fields import NestedField, NamedTupleField
from clickhouse_search.backend.functions import Array, ArrayMap, GtStatsDictGet, Tuple, TupleConcat
from clickhouse_search.models import EntriesSnvIndel, AnnotationsSnvIndel, TranscriptsSnvIndel, Clinvar
from reference_data.models import GENOME_VERSION_GRCh38, GENOME_VERSION_GRCh37
from seqr.models import Sample
from seqr.utils.logging_utils import SeqrLogger
from seqr.utils.search.constants import MAX_VARIANTS, XPOS_SORT_KEY
from settings import CLICKHOUSE_SERVICE_HOSTNAME

logger = SeqrLogger(__name__)

CORE_ENTRIES_FIELDS = ['key', 'xpos']

SEQR_POPULATION_KEY = 'seqrPop'

ANNOTATION_VALUES = {
    field.db_column or field.name: F(f'key__{field.name}') for field in AnnotationsSnvIndel._meta.local_fields
    if field.name not in CORE_ENTRIES_FIELDS
}
ANNOTATION_VALUES['populations'] = TupleConcat(
    ANNOTATION_VALUES['populations'], Tuple(SEQR_POPULATION_KEY),
    output_field=NamedTupleField([
        *AnnotationsSnvIndel.POPULATION_FIELDS,
        ('seqr', GtStatsDictGet.output_field),
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

def clickhouse_backend_enabled():
    return bool(CLICKHOUSE_SERVICE_HOSTNAME)


def get_clickhouse_variants(samples, search, user, previous_search_results, genome_version,page=1, num_results=100, sort=None, **kwargs):
    if genome_version != GENOME_VERSION_GRCh38:
        raise NotImplementedError('Clickhouse search not implemented for genome version other than GRCh38')

    sample_data = _get_sample_data(samples)
    logger.info(f'Loading {Sample.DATASET_TYPE_VARIANT_CALLS} data for {len(sample_data)} families', user)

    entries = EntriesSnvIndel.objects.search(sample_data, **search)
    results = entries.values(
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
    )
    results = results[:MAX_VARIANTS+1]

    sorted_results = sorted(results, key=_get_sort_key(sort))
    total_results = len(sorted_results)
    previous_search_results.update({'all_results': sorted_results, 'total_results': total_results})

    logger.info(f'Total results: {total_results}', user)

    return format_clickhouse_results(sorted_results[(page-1)*num_results:page*num_results])


def format_clickhouse_results(results, **kwargs):
    keys_with_transcripts = [variant['key'] for variant in results if variant['sortedTranscriptConsequences']]
    transcripts_by_key = dict(
        TranscriptsSnvIndel.objects.filter(key__in=keys_with_transcripts).values_list('key', 'transcripts')
    )

    formatted_results = []
    for variant in results:
        transcripts = transcripts_by_key.get(variant['key'], {})
        formatted_variant = {
            **variant,
            'transcripts': transcripts,
            'selectedMainTranscriptId': None,
        }
        # pop sortedTranscriptConsequences from the formatted result and not the original result to ensure the full value is cached properly
        sorted_minimal_transcripts = formatted_variant.pop('sortedTranscriptConsequences')
        main_transcript_id = None
        if sorted_minimal_transcripts:
            main_transcript_id = next(
                t['transcriptId'] for t in transcripts[sorted_minimal_transcripts[0]['geneId']]
                if t['transcriptRank'] == 0
            )
        formatted_results.append({**formatted_variant, 'mainTranscriptId': main_transcript_id})

    return formatted_results


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


def _get_sort_key(sort):
    sort_fields = [XPOS_SORT_KEY]
    if sort and sort != XPOS_SORT_KEY:
        sort_fields.insert(0, sort)

    return lambda x: tuple(x[field] for field in sort_fields)
