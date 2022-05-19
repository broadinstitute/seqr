import argparse
import hail as hl

RENAME_FIELDS = {
    'CN': 'cn', 'QS': 'qs', 'defragmented': 'defragged', 'vaf': 'sf', 'vac': 'sc',
    'genes_any_overlap_totalExons': 'numExon', 'no_ovl_in_round1': 'newCall',
}

def write_main_gcnv_ht(file):
    file_name = file.split('.')[0]
    ht = hl.import_table(f'gs://hail-backend-datasets/{file}', impute=True)
    ht = ht.drop('less_than_50bp')

    annotations = {
        'geneIds': hl.if_else(
            ht.genes_any_overlap_Ensemble_ID == 'null',
            hl.missing(hl.tarray(hl.tstr)),
            ht.genes_any_overlap_Ensemble_ID.split(',').map(lambda gene: gene.split('\.')[0]),
        ),
        'prevCall': hl.is_defined(ht.identical_round1),
        'prevOverlap': hl.is_defined(ht.any_round1),
        'sample_id': ht.sample_fix.first_match_in('(.+)_v\d+_Exome_(C|RP-)\d+$')[0],
        'strvctvre': hl.if_else(ht.strvctvre_score=='not_exonic', hl.missing(hl.tfloat32), hl.float32(ht.strvctvre_score)),
        'svType': 'gCNV_' + ht.svtype,
        'variantId': ht.variant_name + '_' + ht.svtype + '_2',
    }
    ht = ht.annotate(**annotations)
    ht = ht.rename(RENAME_FIELDS)
    ht = ht.select(
        'chr', 'start', 'end',  'genes_LOF_Ensemble_ID', 'genes_CG_Ensemble_ID',
        *annotations.keys(),
        *RENAME_FIELDS.values()
    )

    # Group calls
    gt = ht.group_by('variantId', 'chr', 'svType').aggregate(
        start=hl.agg.min(ht.start),
        end=hl.agg.max(ht.end),
        numExon=hl.agg.max(ht.numExon),
        geneIds=hl.set(hl.agg.collect(ht.geneIds).flatmap(lambda g: g)),
        lof_genes=hl.str(',').join(hl.agg.collect_as_set(ht.genes_LOF_Ensemble_ID)),
        cg_genes=hl.str(',').join(hl.agg.collect_as_set(ht.genes_CG_Ensemble_ID)),
        sc=hl.agg.max(ht.sc),
        sf=hl.agg.max(ht.sf),
        strvctvre=hl.agg.max(ht.strvctvre),
        samples=hl.agg.collect(ht.row),
    ).key_by( 'variantId')

    # Export main variants
    variant_annotations = {
        'interval': hl.interval(
            hl.locus(gt.chr, gt.start, reference_genome='GRCh38'),
            hl.locus(gt.chr, gt.end, reference_genome='GRCh38')),
        'sn': gt.sc/gt.sf,
        'sortedTranscriptConsequences': gt.geneIds.map(lambda gene: hl.Struct(
            gene_id=gene,
            major_consequence=hl.if_else(
                gt.cg_genes.contains(gene),
                'COPY_GAIN',
                hl.if_else(gt.lof_genes.contains(gene), 'LOF',  hl.missing(hl.tstr)),
            ))),
    }
    vt = gt.annotate(**variant_annotations).select(
        'numExon', 'sc', 'sf', 'strvctvre', 'svType', *variant_annotations.keys(),
    )
    vt.write(f'gs://hail-backend-datasets/{file_name}.ht')

    # Export all samples
    st = gt.explode('samples').select('samples', 'start', 'end', 'numExon', 'geneIds')
    st = st.annotate(samples=st.samples.select(
        'sample_id', 'cn', 'start', 'end', 'numExon', 'geneIds', 'defragged', 'prevCall', 'prevOverlap', 'newCall', 'qs'))
    st.write(f'gs://hail-backend-datasets/{file_name}.samples.ht')

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('file')
    args = p.parse_args()

    write_main_gcnv_ht(args.file)