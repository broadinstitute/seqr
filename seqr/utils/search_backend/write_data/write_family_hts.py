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
        **{field: lambda mt: hl.if_else(mt[field] == mt.samples[field], hl.missing(hl.tint32), mt.samples[field])
           for field in ['start', 'end', 'numExon']},
        **{field: lambda mt: hl.int(mt.samples[field]) for field in ['CN', 'QS']},
        **{field: lambda mt: mt.samples[field] for field in ['defragged', 'prevCall', 'prevOverlap', 'newCall']},
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


def write_family_hts(file, project, data_type):
    families_ht = hl.import_table(f'gs://seqr-project-subsets/{project}_fam.csv', key='s', delimiter=',')
    family_guids = families_ht.aggregate(hl.agg.collect_as_set(families_ht.familyGuid))

    mt = hl.read_matrix_table(f'gs://hail-backend-datasets/{file}.mt').select_globals()
    format_mt = FORMAT_MT_IMPORT.get(data_type)
    if format_mt:
        mt = format_mt(mt)
    mt = mt.select_rows()
    print(f'Total MT rows: {mt.rows().count()}')

    mt = mt.semi_join_cols(families_ht)
    mt = mt.filter_rows(hl.agg.any(mt.GT.is_non_ref()))
    annotations = ANNOTATIONS[data_type]
    mt = mt.annotate_entries(**{k: v(mt) for k, v in annotations.items()})

    print(f'Exporting {len(family_guids)} families')
    totals = []
    errors = {}
    for family_guid in family_guids:
        print(family_guid)
        family_subset_ht = families_ht.filter(families_ht.familyGuid == family_guid)

        family_mt = mt.semi_join_cols(family_subset_ht)
        family_mt = family_mt.filter_rows(hl.agg.any(family_mt.GT.is_non_ref()))

        family_ht = family_mt.annotate_rows(entry_agg=hl.agg.collect(hl.struct(
            **{k: family_mt[k] for k in ['s', 'GT', *annotations.keys(), *ENTRY_FIELDS.get(data_type, [])]}
        ))).rows()
        family_ht = family_ht.annotate_globals(
            sample_ids=sorted(family_subset_ht.aggregate(hl.agg.collect(family_subset_ht.s))))
        family_ht = family_ht.transmute(entries=family_ht.sample_ids.map(
            lambda sample_id: family_ht.entry_agg.find(lambda et: et.s == sample_id).drop('s')))
        family_ht = family_ht.repartition(1)

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
    args = p.parse_args()

    write_family_hts(args.file, args.project, args.data_type)