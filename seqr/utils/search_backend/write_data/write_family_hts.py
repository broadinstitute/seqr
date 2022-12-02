import argparse
import hail as hl

ANNOTATIONS = {
    'AB': lambda mt: hl.if_else(mt.AD.length() > 1, hl.float(mt.AD[1] / hl.sum(mt.AD)), hl.missing(hl.tfloat)),
}
ENTRY_FIELDS = ['AD', 'DP', 'GQ', 'GT', 'PL']


def write_family_hts(file, project):
    families_ht = hl.import_table(f'gs://seqr-project-subsets/{project}_fam.csv', key='s', delimiter=',')
    family_guids = families_ht.aggregate(hl.agg.collect_as_set(families_ht.familyGuid))

    mt = hl.read_matrix_table(f'gs://hail-backend-datasets/{file}.mt').select_globals().select_rows()
    print(f'Total MT rows: {mt.rows().count()}')
    mt = mt.semi_join_cols(families_ht)
    mt = mt.filter_rows(hl.agg.any(mt.GT.is_non_ref()))
    mt = mt.annotate_entries(**{k: v(mt) for k, v in ANNOTATIONS.items()})

    print(f'Exporting {len(family_guids)} families')
    totals = []
    errors = {}
    for family_guid in family_guids:
        print(family_guid)
        family_subset_ht = families_ht.filter(families_ht.familyGuid == family_guid)

        family_mt = mt.semi_join_cols(family_subset_ht)
        family_ht = family_mt.filter_rows(hl.agg.any(family_mt.GT.is_non_ref())).entries()
        family_ht = family_ht.select(*ANNOTATIONS.keys(), *ENTRY_FIELDS)

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
    args = p.parse_args()

    write_family_hts(args.file, args.project)