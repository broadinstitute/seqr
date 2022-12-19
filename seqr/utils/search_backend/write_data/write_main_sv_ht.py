import argparse
import hail as hl

CHROMOSOMES = [
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21',
    '22', 'X', 'Y', 'M',
]
CHROM_NUMBER_TO_CHROM = hl.literal({i: chrom for i, chrom in enumerate(CHROMOSOMES)})

SEQR_FIELDS = [
    'rg37_locus', 'rg37_locus_end', 'svType', 'xpos',
]
RENAME_FIELDS = {
    'bothsides_support': 'bothsidesSupport', 'cpx_intervals': 'cpxIntervals', 'sv_type_detail': 'svTypeDetail',
}
CALLSET_FIELDS = {'AF': 'sf', 'AC': 'sc', 'AN': 'sn', 'Het': 'sv_callset_Het', 'Hom': 'sv_callset_Hom'}


def write_main_ht(file):
    ht = hl.read_table(f'gs://hail-backend-datasets/{file}.ht')

    ht = ht.annotate(
        end_chrom=CHROM_NUMBER_TO_CHROM[hl.int(ht.xstop / 1e9) - 1],
        end_pos=hl.int(ht.xstop % int(1e9)),
    )
    ht = ht.annotate(has_end2=(ht.contig != ht.end_chrom) | (ht.end != ht.end_pos))

    variant_annotations = {
        'algorithms': hl.str(',').join(ht.algorithms),
        'filters': hl.set(ht.filters),
        'gnomad_svs': hl.or_missing(hl.is_defined(ht.gnomad_svs_AF), hl.struct(AF=ht.gnomad_svs_AF, ID=ht.gnomad_svs_ID)),
        'interval': hl.interval(
            hl.locus(hl.format('chr%s', ht.contig), ht.start, reference_genome='GRCh38'),
            hl.if_else(
                ht.has_end2 & (ht.svType != 'INS') & (
                    # This is to handle a bug in the SV pipeline, should not go to production
                    (ht.svType != 'CPX') | (hl.is_valid_locus(hl.format('chr%s', ht.end_chrom), ht.end_pos, 'GRCh38'))
                ),
                hl.locus(hl.format('chr%s', ht.end_chrom), ht.end_pos, reference_genome='GRCh38'),
                hl.locus(hl.format('chr%s', ht.contig), ht.end, reference_genome='GRCh38')
            ),
        ),
        'sortedTranscriptConsequences': ht.sortedTranscriptConsequences.map(lambda t: t.select('gene_id', 'major_consequence')),
        'strvctvre': hl.struct(score=ht.StrVCTVRE_score),
        'sv_callset': hl.struct(**{key: ht[field] for key, field in CALLSET_FIELDS.items()}),
        'svSourceDetail': hl.or_missing(ht.has_end2 & (ht.svType == 'INS'), hl.struct(chrom=ht.end_chrom))
    }
    ht = ht.annotate(**variant_annotations)
    ht = ht.rename(RENAME_FIELDS)
    ht = ht.key_by('variantId')
    ht = ht.select_globals().select(*variant_annotations.keys(), *RENAME_FIELDS.values(), *SEQR_FIELDS)

    ht.write(f'gs://hail-backend-datasets/{file}_parsed.ht')


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('file')
    args = p.parse_args()

    write_main_ht(args.file)
