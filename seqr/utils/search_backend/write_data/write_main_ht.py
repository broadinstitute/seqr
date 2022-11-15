import argparse
import hail as hl

SEQR_FIELDS = [
    'AF', 'AC', 'AN', 'cadd', 'clinvar', 'dbnsfp', 'eigen', 'exac', 'filters', 'gnomad_exomes', 'gnomad_genomes',
    'hgmd', 'mpc', 'originalAltAlleles', 'primate_ai', 'rg37_locus', 'rsid', 'splice_ai', 'sortedTranscriptConsequences',
    'topmed', 'variantId', 'xpos',
]

def write_main_ht(file):
    ht =  hl.read_matrix_table(f'gs://hail-backend-datasets/{file}.mt').rows()
    ht = ht.select_globals().select(*SEQR_FIELDS)
    ht.write(f'gs://hail-backend-datasets/{file}.ht')

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('file')
    args = p.parse_args()

    write_main_ht(args.file)