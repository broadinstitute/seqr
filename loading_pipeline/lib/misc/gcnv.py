import hail as hl


def parse_gcnv_genes(gene_col: hl.expr.StringExpression) -> hl.expr.SetExpression:
    return hl.set(
        gene_col.split(',')
        .filter(lambda gene: ~hl.set({'None', 'null', 'NA', ''}).contains(gene))
        .map(lambda gene: gene.split(r'\.')[0]),
    )
