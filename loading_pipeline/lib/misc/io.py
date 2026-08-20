import hashlib
import math
import os
import re
import uuid
from collections.abc import Callable
from string import Template

import hail as hl
import hailtop.fs as hfs
from pyspark.sql import SparkSession

from loading_pipeline.lib.core import DatasetType, Env, ReferenceGenome, Sex
from loading_pipeline.lib.misc.gcnv import parse_gcnv_genes
from loading_pipeline.lib.misc.nested_field import parse_nested_field
from loading_pipeline.lib.misc.validation import SeqrValidationError

BIALLELIC = 2
B_PER_MB = 1 << 20  # 1024 * 1024
MB_PER_PARTITION = 32
MAX_SAMPLES_SPLIT_MULTI_SHUFFLE = 100


def validated_hl_function(
    regex_to_msg: dict[str, str | Template],
) -> Callable[[Callable], Callable]:
    def decorator(fn: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> hl.Table | hl.MatrixTable:
            try:
                t, _ = checkpoint(fn(*args, **kwargs))
            except Exception as e:
                for regex, msg in regex_to_msg.items():
                    match = re.search(regex, str(e))
                    if match and isinstance(msg, Template):
                        msg = msg.substitute(match=match.group(1))  # noqa: PLW2901
                    if match:
                        raise SeqrValidationError(msg) from e
                raise
            else:
                return t

        return wrapper

    return decorator


def file_size_bytes(path: str) -> int:
    if not path.startswith(('gs://', 's3://')):
        path = os.path.abspath(path)

    seen_files = set()

    def traverse(current_path: str) -> int:
        try:
            entries = hfs.ls(current_path)
        except FileNotFoundError:
            return 0

        local_size = 0
        for entry in entries:
            if entry.path in seen_files:
                continue
            seen_files.add(entry.path)

            if entry.typ == hfs.stat_result.FileType.FILE:
                if not entry.path.endswith('.crc'):
                    local_size += entry.size
            elif entry.typ == hfs.stat_result.FileType.DIRECTORY:
                local_size += traverse(entry.path)

        return local_size

    return traverse(path)


def compute_hail_n_partitions(file_size_b: int) -> int:
    return math.ceil(file_size_b / B_PER_MB / MB_PER_PARTITION)


@validated_hl_function(
    {
        'RVD error! Keys found out of order': 'Your callset failed while attempting to split multiallelic sites.  This error can occur if the dataset contains both multiallelic variants and duplicated loci.',
        'array index out of bounds': 'Your callset failed while attempting to split multiallelic sites.  This error can occur if the provided Allele Depth (AD) field does not match the length of the multiallelic site.',
    },
)
def split_multi_hts(
    mt: hl.MatrixTable,
    skip_validate_no_duplicate_variants: bool,
    max_samples_split_multi_shuffle=MAX_SAMPLES_SPLIT_MULTI_SHUFFLE,
) -> hl.MatrixTable:
    bi = mt.filter_rows(hl.len(mt.alleles) == BIALLELIC)
    # split_multi_hts filters star alleles by default, but we
    # need that behavior for bi-allelic variants in addition to
    # multi-allelics
    bi = bi.filter_rows(~bi.alleles.contains('*'))
    bi = bi.annotate_rows(a_index=1, was_split=False)
    multi = mt.filter_rows(hl.len(mt.alleles) > BIALLELIC)
    split = hl.split_multi_hts(
        multi,
        permit_shuffle=mt.count()[1] < max_samples_split_multi_shuffle,
    )
    mt = split.union_rows(bi)
    # If we've disabled validation (which is expected to throw an exception
    # for duplicate variants, we would like to distinc )
    if skip_validate_no_duplicate_variants:
        return mt.distinct_by_row()
    return mt


def import_gcnv_bed_file(callset_path: str) -> hl.MatrixTable:
    # Hail falls over itself with OOMs with use_new_shuffle here... no clue why.
    hl._set_flags(use_new_shuffle=None, no_whole_stage_codegen='1')  # noqa: SLF001
    ht = hl.import_table(
        callset_path,
        types={
            **DatasetType.GCNV.col_fields,
            **DatasetType.GCNV.entries_fields,
            **DatasetType.GCNV.row_fields,
        },
        force=callset_path.endswith('gz'),
    )
    mt = ht.to_matrix_table(
        row_key=['variant_name', 'svtype'],
        col_key=['sample_fix'],
        row_fields=['chr', 'sc', 'sf', 'strvctvre_score'],
    )
    mt = mt.rename({'start': 'sample_start', 'end': 'sample_end'})
    mt = mt.key_cols_by(s=mt.sample_fix)
    mt = mt.annotate_rows(
        variant_id=hl.format('%s_%s', mt.variant_name, mt.svtype),
        filters=hl.empty_set(hl.tstr),
        start=hl.agg.min(mt.sample_start),
        end=hl.agg.max(mt.sample_end),
        num_exon=hl.agg.max(mt.genes_any_overlap_totalExons),
        gene_ids=hl.flatten(
            hl.agg.collect_as_set(parse_gcnv_genes(mt.genes_any_overlap_Ensemble_ID)),
        ),
        cg_genes=hl.flatten(
            hl.agg.collect_as_set(parse_gcnv_genes(mt.genes_CG_Ensemble_ID)),
        ),
        lof_genes=hl.flatten(
            hl.agg.collect_as_set(parse_gcnv_genes(mt.genes_LOF_Ensemble_ID)),
        ),
    )
    return mt.unfilter_entries()


@validated_hl_function(
    {
        '.*FileNotFoundException|GoogleJsonResponseException: 403 Forbidden|arguments refer to no files.*': 'Unable to access the VCF in cloud storage.',
        # NB: ?: is non-capturing group.
        '.*(?:InvalidHeader|VCFParseError): (.*)$': Template(
            'VCF failed file format validation: $match',
        ),
        '.*IOException: Gzip-compressed data is corrupt.*': 'Gzip-compressed data is corrupt.',
    },
)
def import_vcf(
    callset_path: str,
    reference_genome: ReferenceGenome,
) -> hl.MatrixTable:
    args = {
        'reference_genome': reference_genome.value,
        'skip_invalid_loci': True,
        'contig_recoding': reference_genome.contig_recoding(),
        'find_replace': (
            'nul',
            '.',
        ),  # Required for internal exome callsets (+ some AnVIL requests)
        'array_elements_required': False,
        'call_fields': [],  # PGT is unused downstream, but is occasionally present in old VCFs!
    }
    try:
        mt, _ = checkpoint(
            hl.import_vcf(
                callset_path,
                force_bgz=True,
                **args,
            ),
        )
    except Exception as e:
        # Handle callsets provided as gz but not bgz
        # Note that this is handled separately from other VCF validation
        # as it's an exceptional case that we can handle internally.
        if 'File does not conform to block gzip format' not in str(e):
            raise
        mt = hl.import_vcf(
            callset_path,
            force=True,
            **args,
        )
    return mt


def import_callset(
    callset_path: str,
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
) -> hl.MatrixTable:
    if dataset_type == DatasetType.GCNV:
        mt = import_gcnv_bed_file(callset_path)
    elif 'vcf' in callset_path:
        mt = import_vcf(callset_path, reference_genome)
    elif 'mt' in callset_path:
        mt = hl.read_matrix_table(callset_path)
    if dataset_type == DatasetType.SV:
        mt = mt.annotate_rows(
            variant_id=mt.rsid,
        )
    return mt.key_rows_by(*dataset_type.table_key_type(reference_genome).fields)


def import_parquet(
    callset_path: str,
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
) -> hl.HailTable:
    spark = SparkSession.builder.getOrCreate()
    df = spark.read.parquet(callset_path)
    ht = hl.Table.from_spark(df)

    key_fields = dataset_type.table_key_type(reference_genome).fields
    if 'locus' in key_fields:
        ht = ht.annotate(
            locus=hl.Locus(
                contig=ht.variant_id.split('-')[0],
                position=ht.variant_id.split('-')[1],
                reference_genome=reference_genome.value,
            ),
            alleles=[ht.variant_id.split('-')[2], ht.variant_id.split('-')[3]],
        )

    return ht.key_by(*key_fields)


@validated_hl_function(
    {
        'instance has no field (.*)': Template(
            'Your callset is missing a required field: $match',
        ),
    },
)
def select_relevant_fields(
    mt: hl.MatrixTable,
    dataset_type: DatasetType,
    additional_row_fields: None | dict[str, hl.expr.types.HailType | set] = None,
) -> hl.MatrixTable:
    mt = mt.select_globals()
    mt = mt.select_rows(
        **{field: parse_nested_field(mt, field) for field in dataset_type.row_fields},
        **{
            field: parse_nested_field(mt, field)
            for field in (additional_row_fields or [])
        },
    )
    mt = mt.select_cols(
        **{field: parse_nested_field(mt, field) for field in dataset_type.col_fields},
    )
    return mt.select_entries(
        **{
            field: parse_nested_field(mt, field)
            for field in dataset_type.entries_fields
        },
    )


def import_imputed_sex(imputed_sex_path: str) -> hl.Table:
    ht = hl.import_table(imputed_sex_path)
    imputed_sex_lookup = hl.dict(
        {
            imputed_sex_value: s.value
            for s in Sex
            for imputed_sex_value in s.imputed_sex_values
        },
    )
    ht = ht.select(
        s=ht.collaborator_sample_id,
        predicted_sex=(
            hl.case()
            .when(
                imputed_sex_lookup.contains(ht.predicted_sex),
                imputed_sex_lookup[ht.predicted_sex],
            )
            .or_error(
                hl.format(
                    'Found unexpected value %s in imputed sex file',
                    ht.predicted_sex,
                ),
            )
        ),
    )
    return ht.key_by(ht.s)


def import_tdr_qc_metrics(file_path: str) -> hl.Table:
    ht = hl.import_table(
        file_path,
        types={
            'contamination_rate': hl.tfloat32,
            'percent_bases_at_20x': hl.tfloat32,
            'mean_coverage': hl.tfloat32,
        },
        delimiter='\t',
        missing=[''],
    )
    ht = ht.select(
        s=ht.collaborator_sample_id,
        contamination_rate=ht.contamination_rate,
        percent_bases_at_20x=ht.percent_bases_at_20x,
        mean_coverage=ht.mean_coverage,
    )
    return ht.key_by(ht.s)


def import_pedigree(pedigree_path: str) -> hl.Table:
    ht = hl.import_table(pedigree_path, missing='')
    optional_selects = {'remap_id': ht.VCF_ID} if 'VCF_ID' in ht.row else {}
    return ht.select(
        sex=ht.Sex,
        family_guid=ht.Family_GUID,
        s=ht.Individual_ID,
        maternal_s=ht.Maternal_ID,
        paternal_s=ht.Paternal_ID,
        **optional_selects,
    )


def remap_pedigree_hash(pedigree_path: str) -> hl.Int32Expression:
    sha256 = hashlib.sha256()
    with hfs.open(pedigree_path) as f2:
        sha256.update(f2.read().encode('utf8'))
    # maximum 4 byte int
    return hl.int32(int(sha256.hexdigest()[:8], 16))


def checkpoint(
    t: hl.Table | hl.MatrixTable,
) -> tuple[hl.Table | hl.MatrixTable, str]:
    suffix = 'mt' if isinstance(t, hl.MatrixTable) else 'ht'
    read_fn = hl.read_matrix_table if isinstance(t, hl.MatrixTable) else hl.read_table
    checkpoint_path = os.path.join(
        Env.HAIL_TMP_DIR,
        f'{uuid.uuid4()}.{suffix}',
    )
    t.write(checkpoint_path)
    return read_fn(checkpoint_path), checkpoint_path


def write(
    t: hl.Table | hl.MatrixTable,
    destination_path: str,
    repartition: bool = True,
) -> hl.Table | hl.MatrixTable:
    t, path = checkpoint(t)
    if repartition:
        t = t.repartition(
            compute_hail_n_partitions(file_size_bytes(path)),
            shuffle=False,
        )
    return t.write(destination_path, overwrite=True)
