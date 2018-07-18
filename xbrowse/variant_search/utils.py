
def filter_gene_variants_by_variant_filter(variants, gene_id, variant_filter):
    """
    When you switch a variant stream to gene stream,
    result is a list of all variants for a given gene.
    But some of the fields in variant_filter are specific to a gene annotation
    (currently only the so_annotations field)

    Returns a list of variants with only variants whose annotations are relevant to this gene
    """
    if variant_filter is None:
        return variants
    if not variant_filter.so_annotations:
        return variants
    new_variants = []
    for variant in variants:
        for annot in variant.annotation.get('vep_annotation', []):
            if ('gene' not in annot or annot['gene'] != gene_id) and ('gene_id' not in annot or annot['gene_id'] != gene_id):
                continue
            if annot.get('consequence') in variant_filter.so_annotations or annot.get('major_consequence') in variant_filter.so_annotations:
                new_variants.append(variant)
                break  # break out of inner loop

    return new_variants
