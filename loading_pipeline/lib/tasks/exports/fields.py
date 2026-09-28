import hail as hl

from loading_pipeline.lib.annotations.shared import variant_id, xpos
from loading_pipeline.lib.core import DatasetType, SampleType


def _get_calls_export_fields(
    fe: hl.Struct,
    dataset_type: DatasetType,
):
    return {
        DatasetType.SNV_INDEL: lambda fe: hl.Struct(
            sampleId=fe.s,
            gt=fe.GT.n_alt_alleles(),
            gq=fe.GQ,
            ab=fe.AB,
            dp=fe.DP,
        ),
        DatasetType.MITO: lambda fe: hl.Struct(
            sampleId=fe.s,
            gt=fe.GT.n_alt_alleles(),
            dp=fe.DP,
            hl=fe.HL,
            mitoCn=fe.mito_cn,
            contamination=fe.contamination,
        ),
        DatasetType.SV: lambda fe: hl.Struct(
            sampleId=fe.s,
            gt=fe.GT.n_alt_alleles(),
            cn=fe.CN,
            gq=fe.GQ,
            newCall=fe.concordance.new_call,
            prevCall=fe.concordance.prev_call,
            prevNumAlt=fe.concordance.prev_num_alt,
        ),
        DatasetType.GCNV: lambda fe: hl.Struct(
            sampleId=fe.s,
            gt=fe.GT.n_alt_alleles(),
            cn=fe.CN,
            qs=fe.QS,
            defragged=fe.defragged,
            start=fe.sample_start,
            end=fe.sample_end,
            numExon=fe.sample_num_exon,
            geneIds=fe.sample_gene_ids,
            newCall=fe.concordance.new_call,
            prevCall=fe.concordance.prev_call,
            prevOverlap=fe.concordance.prev_overlap,
        ),
    }[dataset_type](fe)


def get_entries_export_fields(
    ht: hl.Table,
    dataset_type: DatasetType,
    sample_type: SampleType,
):
    return {
        'project_guid': ht.family_entries.project_guid[0],
        'family_guid': ht.family_entries.family_guid[0],
        **(
            {
                'sample_type': sample_type.value,
                'variantId': variant_id(ht),
                'xpos': xpos(ht),
            }
            if dataset_type in {DatasetType.SNV_INDEL, DatasetType.MITO}
            else {'variantId': ht.variant_id}
        ),
        'filters': ht.filters,
        'calls': hl.sorted(ht.family_entries, key=lambda fe: fe.s).map(
            lambda fe: _get_calls_export_fields(fe, dataset_type),
        ),
        'sign': 1,
    }
