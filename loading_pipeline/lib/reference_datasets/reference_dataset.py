import importlib
import types
from collections.abc import Callable
from enum import StrEnum

import hail as hl

from loading_pipeline.lib.annotations import sv
from loading_pipeline.lib.core import (
    DatasetType,
    ReferenceGenome,
)
from loading_pipeline.lib.misc.validation import (
    validate_allele_type,
    validate_no_duplicate_variants,
)
from loading_pipeline.lib.reference_datasets.misc import (
    compress_floats,
    filter_contigs,
)

DATASET_TYPES = 'dataset_types'
FORMATTING_ANNOTATION = 'formatting_annotation'
SELECT = 'select'
VERSION = 'version'
PATH = 'path'


class ReferenceDataset(StrEnum):
    eigen = 'eigen'
    splice_ai = 'splice_ai'
    topmed = 'topmed'
    gnomad_coding_and_noncoding = 'gnomad_coding_and_noncoding'
    gnomad_exomes = 'gnomad_exomes'
    gnomad_genomes = 'gnomad_genomes'
    gnomad_qc = 'gnomad_qc'
    gnomad_svs = 'gnomad_svs'

    @property
    def formatting_annotation(self) -> Callable | None:
        return CONFIG[self].get(FORMATTING_ANNOTATION)

    def version(self, reference_genome: ReferenceGenome) -> str:
        version = CONFIG[self][reference_genome][VERSION]
        if isinstance(version, types.FunctionType):
            return version(
                self.path(reference_genome),
            )
        return version

    def dataset_types(
        self,
        reference_genome: ReferenceGenome,
    ) -> frozenset[DatasetType]:
        return CONFIG[self].get(reference_genome, {}).get(DATASET_TYPES, frozenset())

    @property
    def select(
        self,
    ) -> Callable[[ReferenceGenome, DatasetType, hl.Table], hl.Table] | None:
        return CONFIG[self].get(SELECT)

    def path(self, reference_genome: ReferenceGenome) -> str | list[str]:
        return CONFIG[self][reference_genome][PATH]

    def get_ht(
        self,
        reference_genome: ReferenceGenome,
    ) -> hl.Table:
        module = importlib.import_module(
            f'loading_pipeline.lib.reference_datasets.{self.name}',
        )
        path = self.path(reference_genome)
        ht = module.get_ht(path, reference_genome)
        ht = compress_floats(ht)
        ht = filter_contigs(ht, reference_genome)
        for dataset_type in self.dataset_types(reference_genome):
            validate_allele_type(ht, dataset_type)
            validate_no_duplicate_variants(ht, reference_genome, dataset_type)
        return ht


CONFIG = {
    ReferenceDataset.eigen: {
        ReferenceGenome.GRCh37: {
            DATASET_TYPES: frozenset([DatasetType.SNV_INDEL]),
            VERSION: '1.1',
            # NB: The download link on the Eigen website (http://www.columbia.edu/~ii2135/download.html) is broken
            # as of 11/15/24 so we will host the data
            PATH: 'gs://seqr-reference-data/GRCh37/eigen/EIGEN_coding_noncoding.grch37.ht',
        },
        ReferenceGenome.GRCh38: {
            DATASET_TYPES: frozenset([DatasetType.SNV_INDEL]),
            VERSION: '1.1',
            PATH: 'gs://seqr-reference-data/GRCh38/eigen/EIGEN_coding_noncoding.liftover_grch38.ht',
        },
    },
    ReferenceDataset.splice_ai: {
        ReferenceGenome.GRCh37: {
            DATASET_TYPES: frozenset([DatasetType.SNV_INDEL]),
            VERSION: '1.1',
            PATH: [
                'gs://seqr-reference-data/GRCh37/spliceai/spliceai_scores.masked.snv.hg19.vcf.gz',
                'gs://seqr-reference-data/GRCh37/spliceai/spliceai_scores.masked.indel.hg19.vcf.gz',
            ],
        },
        ReferenceGenome.GRCh38: {
            DATASET_TYPES: frozenset([DatasetType.SNV_INDEL]),
            VERSION: '1.1',
            # NB: SpliceAI data is only available to download for authenticated Illumina users, so we will host the data
            PATH: [
                'gs://seqr-reference-data/GRCh38/spliceai/spliceai_scores.masked.snv.hg38.vcf.gz',
                'gs://seqr-reference-data/GRCh38/spliceai/spliceai_scores.masked.indel.hg38.vcf.gz',
            ],
        },
    },
    ReferenceDataset.topmed: {
        ReferenceGenome.GRCh37: {
            DATASET_TYPES: frozenset([DatasetType.SNV_INDEL]),
            VERSION: '1.1',
            PATH: 'gs://seqr-reference-data/GRCh37/TopMed/bravo-dbsnp-all.removed_chr_prefix.liftunder_GRCh37.vcf.gz',
        },
        ReferenceGenome.GRCh38: {
            DATASET_TYPES: frozenset([DatasetType.SNV_INDEL]),
            VERSION: '1.1',
            # NB: TopMed data is available to download via https://legacy.bravo.sph.umich.edu/freeze8/hg38/downloads/vcf/<chrom>
            # However, users must be authenticated and accept TOS to access it so for now we will host a copy of the data
            PATH: 'gs://seqr-reference-data/GRCh38/TopMed/bravo-dbsnp-all.vcf.gz',
        },
    },
    ReferenceDataset.gnomad_exomes: {
        ReferenceGenome.GRCh37: {
            DATASET_TYPES: frozenset([DatasetType.SNV_INDEL]),
            VERSION: '1.0',
            PATH: 'gs://gcp-public-data--gnomad/release/2.1.1/ht/exomes/gnomad.exomes.r2.1.1.sites.ht',
        },
        ReferenceGenome.GRCh38: {
            DATASET_TYPES: frozenset([DatasetType.SNV_INDEL]),
            VERSION: '1.0',
            PATH: 'gs://gcp-public-data--gnomad/release/4.1/ht/exomes/gnomad.exomes.v4.1.sites.ht',
        },
    },
    ReferenceDataset.gnomad_genomes: {
        ReferenceGenome.GRCh37: {
            DATASET_TYPES: frozenset([DatasetType.SNV_INDEL]),
            VERSION: '1.0',
            PATH: 'gs://gcp-public-data--gnomad/release/2.1.1/ht/genomes/gnomad.genomes.r2.1.1.sites.ht',
        },
        ReferenceGenome.GRCh38: {
            DATASET_TYPES: frozenset([DatasetType.SNV_INDEL]),
            VERSION: '1.0',
            PATH: 'gs://gcp-public-data--gnomad/release/4.1/ht/genomes/gnomad.genomes.v4.1.sites.ht',
        },
    },
    ReferenceDataset.gnomad_qc: {
        ReferenceGenome.GRCh37: {
            DATASET_TYPES: frozenset([DatasetType.SNV_INDEL]),
            VERSION: '1.0',
            PATH: 'gs://seqr-reference-data/gnomad_qc/GRCh37/gnomad.joint.high_callrate_common_biallelic_snps.pruned.mt',
        },
        ReferenceGenome.GRCh38: {
            DATASET_TYPES: frozenset([DatasetType.SNV_INDEL]),
            VERSION: '1.0',
            PATH: 'gs://gcp-public-data--gnomad/release/4.0/pca/gnomad.v4.0.pca_loadings.ht',
        },
    },
    ReferenceDataset.gnomad_svs: {
        FORMATTING_ANNOTATION: sv.gnomad_svs,
        ReferenceGenome.GRCh38: {
            DATASET_TYPES: frozenset([DatasetType.SV]),
            VERSION: '1.1',
            PATH: 'gs://gcp-public-data--gnomad/release/4.1/genome_sv/gnomad.v4.1.sv.sites.vcf.gz',
        },
    },
}
CONFIG[ReferenceDataset.gnomad_coding_and_noncoding] = {
    **CONFIG[ReferenceDataset.gnomad_genomes],
}
