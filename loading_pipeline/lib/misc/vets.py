import hail as hl

VETS_SNP_CUTOFF = 0.997
VETS_INDEL_CUTOFF = 0.99
VETS_SNP_FILTER = 'high_CALIBRATION_SENSITIVITY_SNP'
VETS_INDEL_FILTER = 'high_CALIBRATION_SENSITIVITY_INDEL'


def annotate_vets(mt: hl.MatrixTable) -> hl.MatrixTable:
    if not hasattr(mt, 'info.CALIBRATION_SENSITIVITY'):
        return mt
    return mt.annotate_rows(
        filters=hl.bind(
            lambda is_snp, split_cs: (
                hl.case()
                .when(
                    is_snp & (split_cs > VETS_SNP_CUTOFF),
                    hl.if_else(
                        hl.is_defined(mt.filters),
                        mt.filters.add(VETS_SNP_FILTER),
                        hl.set([VETS_SNP_FILTER]),
                    ),
                )
                .when(
                    ~is_snp & (split_cs > VETS_INDEL_CUTOFF),
                    hl.if_else(
                        hl.is_defined(mt.filters),
                        mt.filters.add(VETS_INDEL_FILTER),
                        hl.set([VETS_INDEL_FILTER]),
                    ),
                )
                .default(
                    mt.filters,
                )
            ),
            hl.is_snp(mt.alleles[0], mt.alleles[1]),
            hl.parse_float(mt['info.CALIBRATION_SENSITIVITY'][mt.a_index - 1]),
        ),
    )
