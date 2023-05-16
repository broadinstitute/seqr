import argparse
import hail as hl

RENAME_FIELDS = {
    'defragmented': 'defragged', 'genes_any_overlap_totalExons': 'numExon', 'no_ovl_in_round1': 'newCall',
}

def write_main_gcnv_ht(file):
    file_name = file.split('.')[0]
    ht = hl.import_table(f'gs://hail-backend-datasets/{file}', impute=True)

    annotations = {
        'geneIds': hl.if_else(
            ht.genes_any_overlap_Ensemble_ID == 'null',
            hl.missing(hl.tarray(hl.tstr)),
            ht.genes_any_overlap_Ensemble_ID.split(',').map(lambda gene: gene.split('\.')[0]),
        ),
        'prevCall': hl.is_defined(ht.identical_round1),
        'prevOverlap': hl.is_defined(ht.any_round1),
        'sample_id': ht.sample_fix.first_match_in('(.+)_v\d+_Exome_(C|RP-)\d+$')[0],
        'strvctvre': hl.parse_float(ht.strvctvre_score),
        'svType': 'gCNV_' + ht.svtype,
        'variantId': ht.variant_name + '_' + ht.svtype + '_2',
    }
    ht = ht.annotate(**annotations)
    ht = ht.rename(RENAME_FIELDS)
    ht = ht.select(
        'chr', 'start', 'end',  'genes_LOF_Ensemble_ID', 'genes_CG_Ensemble_ID', 'vaf', 'vac', 'CN', 'QS',
        *annotations.keys(),
        *RENAME_FIELDS.values()
    )

    # Group calls
    gt = ht.group_by('variantId', 'chr', 'svType').aggregate(
        start=hl.agg.min(ht.start),
        end=hl.agg.max(ht.end),
        num_exon=hl.agg.max(ht.numExon),
        geneIds=hl.set(hl.agg.collect(ht.geneIds).flatmap(lambda g: g)),
        lof_genes=hl.str(',').join(hl.agg.collect_as_set(ht.genes_LOF_Ensemble_ID)),
        cg_genes=hl.str(',').join(hl.agg.collect_as_set(ht.genes_CG_Ensemble_ID)),
        vac=hl.agg.max(ht.vac),
        vaf=hl.agg.max(ht.vaf),
        strvctvre=hl.agg.max(ht.strvctvre),
        samples=hl.agg.collect(ht.row),
    ).key_by('variantId')

    hl.get_reference('GRCh38').add_liftover(
        'gs://hail-common/references/grch38_to_grch37.over.chain.gz',  hl.get_reference('GRCh37'))
    start_locus = hl.locus(gt.chr, gt.start, reference_genome='GRCh38')
    end_locus = hl.locus(gt.chr, gt.end, reference_genome='GRCh38')
    vt = gt.annotate(
        interval=hl.interval(start_locus, end_locus),
        rg37_locus=hl.liftover(start_locus, 'GRCh37'),
        rg37_locus_end=hl.liftover(end_locus, 'GRCh37'),
    )
    vt.write(f'gs://hail-backend-datasets/{file_name}.grouped.ht')

    # Export all samples
    st = gt.explode('samples').select('samples', 'start', 'end', 'numExon', 'geneIds')
    st = st.annotate(s=st.samples.sample_id, samples=st.samples.select(
        'sample_id', 'CN', 'start', 'end', 'numExon', 'geneIds', 'defragged', 'prevCall', 'prevOverlap', 'newCall', 'QS'))
    samples_mt = st.to_matrix_table(row_key=['variantId'], col_key=['s'])
    samples_mt.write(f'gs://hail-backend-datasets/{file_name}.mt')


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('file')
    args = p.parse_args()

    write_main_gcnv_ht(args.file)