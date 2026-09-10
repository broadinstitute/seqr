import hail as hl


def get_ht(path: str, *_) -> hl.Table:
    ht = hl.read_table(path)
    ht = ht.select(Eigen_phred=hl.float32(ht.info['Eigen-phred']))
    return ht.group_by(*ht.key).aggregate(Eigen_phred=hl.agg.max(ht.Eigen_phred))
