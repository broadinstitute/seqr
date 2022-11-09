import argparse
import hail as hl

SEQR_FIELDS = [
    # shared variant fields
    'clinvar', 'dbnsfp', 'filters', 'rg37_locus', 'rsid', 'sortedTranscriptConsequences', 'variantId', 'xpos',
    # mito specific fields
    'mitomap', 'mitimpact_apogee', 'hmtvar_hmtVar', 'common_low_heteroplasmy', 'hap_defining_variant',
    'mitotip_mitoTIP', 'high_constraint_region',
]

def write_main_ht(file):
    ht = hl.read_matrix_table(f'gs://hail-backend-datasets/{file}.mt').rows()
    annotations = {
        'callset': hl.struct(
            AF=ht.AF,
            AC=ht.AC,
            AN=ht.AN,
        ),
        'callset_heteroplasmy': hl.struct(
            AF=ht.AF_het,
            AC=ht.AC_het,
            AN=ht.AN,
        ),
        'gnomad_mito': hl.struct(
            AF=ht.gnomad_mito.AF,
            AC=ht.gnomad_mito.AC,
            AN=ht.gnomad_mito.AN,
        ),
        'gnomad_mito_heteroplasmy': hl.struct(
            AF=ht.gnomad_mito.AF_het,
            AC=ht.gnomad_mito.AC_het,
            AN=ht.gnomad_mito.AN,
            max_hl=ht.gnomad_mito.max_hl,
        ),
        'helix': hl.struct(
            AF=ht.helix.AF,
            AC=ht.helix.AC,
            AN=ht.helix.AN,
        ),
        'helix_heteroplasmy': hl.struct(
            AF=ht.helix.AF_het,
            AC=ht.helix.AC_het,
            AN=ht.helix.AN,
            max_hl=ht.helix.max_hl,
        ),
    }
    ht = ht.annotate(**annotations)
    ht = ht.select_globals().select(*SEQR_FIELDS, *annotations.keys())
    ht.write(f'gs://hail-backend-datasets/{file}.ht')


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('file')
    args = p.parse_args()

    write_main_ht(args.file)