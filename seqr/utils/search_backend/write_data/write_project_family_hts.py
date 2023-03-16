import argparse
import hail as hl

VARIANT_TYPE = 'VARIANTS'
SV_TYPE = 'SV'
GCNV_TYPE = 'gCNV'
MITO_TYPE = 'MITO'

FORMAT_MT_IMPORT = {
    SV_TYPE: lambda mt: mt.rename({'rsid': 'variantId'}).key_rows_by('variantId'),
    GCNV_TYPE: lambda mt: mt.annotate_entries(
        GT=hl.if_else((mt.samples.CN == 0) | (mt.samples.CN > 3), hl.Call([1, 1]), hl.Call([0, 1]))
    ),
    MITO_TYPE: lambda mt: mt.transmute_cols(c_mito_cn=mt.mito_cn, c_contamination=mt.contamination),
}


def _get_samples_field(field):
    return lambda mt: mt.samples[field]


def _get_samples_override_field(field):
    return lambda mt: hl.if_else(mt[field] == mt.samples[field], hl.missing(hl.tint32), mt.samples[field])


ANNOTATIONS = {
    VARIANT_TYPE: {
        'AB': lambda mt: hl.if_else(
            (mt.AD.length() > 1) & (hl.sum(mt.AD) != 0), hl.float(mt.AD[1] / hl.sum(mt.AD)), hl.missing(hl.tfloat),
        ),
    },
    SV_TYPE: {
        'CN': lambda mt: mt.RD_CN,
        'GQ_SV': lambda mt: mt.GQ,
    },
    GCNV_TYPE: dict(
        geneIds=lambda mt: hl.if_else(mt.geneIds == hl.set(mt.samples.geneIds), hl.missing(hl.tarray(hl.tstr)), mt.samples.geneIds),
        **{field: _get_samples_override_field(field) for field in ['start', 'end', 'numExon']},
        **{field: _get_samples_field(field) for field in ['CN', 'QS', 'defragged', 'prevCall', 'prevOverlap', 'newCall']},
    ),
    MITO_TYPE: {
        'GQ': lambda mt: hl.int(mt.MQ),
        'mito_cn': lambda mt: mt.c_mito_cn,
        'contamination': lambda mt: mt.c_contamination,
    },
}
ENTRY_FIELDS = {
    VARIANT_TYPE: ['AD', 'DP', 'GQ', 'PL'],
    MITO_TYPE: ['DP', 'HL'],
}


def _write_entries_ht(mt, data_type, sample_ids, num_partitions=1):
    ht = mt.annotate_rows(entry_agg=hl.agg.collect(hl.struct(
        **{k: mt[k] for k in ['s', 'GT', *ANNOTATIONS[data_type].keys(), *ENTRY_FIELDS.get(data_type, [])]}
    ))).rows()
    ht = ht.annotate_globals(sample_ids=sorted(sample_ids))
    ht = ht.annotate(entries=ht.sample_ids.map(
        lambda sample_id: ht.entry_agg.find(lambda et: et.s == sample_id).drop('s'))).drop('entry_agg')
    ht = ht.repartition(num_partitions)
    return ht


def write_project_family_hts(file, project, data_type, skip_write_project=False, skip_write_families=False):
    families_ht = hl.import_table(f'gs://seqr-project-subsets/{project}_fam.csv', key='s', delimiter=',')
    family_guids = families_ht.aggregate(hl.agg.collect_as_set(families_ht.familyGuid))
    sample_ids = families_ht.aggregate(hl.agg.collect_as_set(families_ht.s))

    mt = hl.read_matrix_table(f'gs://hail-backend-datasets/{file}.mt').select_globals()
    format_mt = FORMAT_MT_IMPORT.get(data_type)
    if format_mt:
        mt = format_mt(mt)
    mt = mt.select_rows()
    print(f'Total MT rows: {mt.rows().count()}')

    project_mt = mt.semi_join_cols(families_ht)
    missing_samples = sample_ids - project_mt.aggregate_cols(hl.agg.collect_as_set(project_mt.s))
    if missing_samples:
        mt_sample_ids = mt.aggregate_cols(hl.agg.collect_as_set(mt.s))
        raise ValueError(
            f'The following {len(missing_samples)} samples are missing from the main mt: {", ".join(sorted(missing_samples))}\n'
            f'Found Samples: {", ".join(sorted(mt_sample_ids))}'
        )

    mt = project_mt.filter_rows(hl.agg.any(project_mt.GT.is_non_ref()))
    mt = mt.annotate_entries(**{k: v(mt) for k, v in ANNOTATIONS[data_type].items()})
    
    if skip_write_project:
        print('Skipping project export')
    else:
        print('Exporting project')
        project_ht = _write_entries_ht(mt, data_type, sample_ids=sample_ids)
        count = project_ht.count()
        print(f'Project {project}: {families_ht.count()} samples, {count} rows')
        project_ht.write(f'gs://hail-backend-datasets/{file}__projects/{project}.ht')
    
    if skip_write_families:
        print('Skipping families export')
        return

    print(f'Exporting {len(family_guids)} families')
    totals = []
    errors = {}
    for family_guid in family_guids:
        print(family_guid)
        family_subset_ht = families_ht.filter(families_ht.familyGuid == family_guid)

        family_mt = mt.semi_join_cols(family_subset_ht)
        family_mt = family_mt.filter_rows(hl.agg.any(family_mt.GT.is_non_ref()))

        family_ht = _write_entries_ht(
            family_mt, data_type, sample_ids=family_subset_ht.aggregate(hl.agg.collect(family_subset_ht.s)))

        count = family_ht.count()
        print(f'{family_guid}: {family_subset_ht.count()} samples, {count} rows')
        totals.append(count)

        try:
            family_ht.write(f'gs://hail-backend-datasets/{file}__families/{family_guid}.ht')
        except Exception as e:
            errors[family_guid] = str(e)

    for family_guid, err in errors.items():
        print(f'ERROR writing {family_guid}: {err}')

    print(f'Family Table Counts: {totals}')
    print(f'Average rows per table: {sum(totals)/len(totals)}')


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('file')
    p.add_argument('project')
    p.add_argument('data_type', choices=ANNOTATIONS.keys())
    p.add_argument('--skip-write-project', action='store_true')
    p.add_argument('--skip-write-families', action='store_true')
    args = p.parse_args()

    write_project_family_hts(
        args.file, args.project, args.data_type,
        skip_write_project=args.skip_write_project, skip_write_families=args.skip_write_families)