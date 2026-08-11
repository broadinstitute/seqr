CREATE TABLE `GRCh38/SNV_INDEL/variants_disk`
(
    `key` UInt32 CODEC(Delta(8), ZSTD(1)),
    `sortedTranscriptConsequences` Nested(alphamissensePathogenicity Nullable(Decimal(9, 5)), canonical Nullable(UInt8), consequenceTerms Array(Nullable(Enum8('transcript_ablation' = 1, 'splice_acceptor_variant' = 2, 'splice_donor_variant' = 3, 'stop_gained' = 4, 'frameshift_variant' = 5, 'stop_lost' = 6, 'start_lost' = 7, 'inframe_insertion' = 8, 'inframe_deletion' = 9, 'missense_variant' = 10, 'protein_altering_variant' = 11, 'splice_donor_5th_base_variant' = 12, 'splice_region_variant' = 13, 'splice_donor_region_variant' = 14, 'splice_polypyrimidine_tract_variant' = 15, 'incomplete_terminal_codon_variant' = 16, 'start_retained_variant' = 17, 'stop_retained_variant' = 18, 'synonymous_variant' = 19, 'coding_sequence_variant' = 20, 'mature_miRNA_variant' = 21, '5_prime_UTR_variant' = 22, '3_prime_UTR_variant' = 23, 'non_coding_transcript_exon_variant' = 24, 'intron_variant' = 25, 'NMD_transcript_variant' = 26, 'non_coding_transcript_variant' = 27, 'coding_transcript_variant' = 28, 'upstream_gene_variant' = 29, 'downstream_gene_variant' = 30, 'intergenic_variant' = 31, 'sequence_variant' = 32))), extendedIntronicSpliceRegionVariant Nullable(Bool), fiveutrConsequence Nullable(Enum8('5_prime_UTR_premature_start_codon_gain_variant' = 1, '5_prime_UTR_premature_start_codon_loss_variant' = 2, '5_prime_UTR_stop_codon_gain_variant' = 3, '5_prime_UTR_stop_codon_loss_variant' = 4, '5_prime_UTR_uORF_frameshift_variant' = 5)), geneId Nullable(String)),
    `sortedMotifFeatureConsequences` Nested(consequenceTerms Array(Nullable(Enum8('TFBS_ablation' = 0, 'TFBS_amplification' = 1, 'TF_binding_site_variant' = 2, 'TFBS_fusion' = 3, 'TFBS_translocation' = 4)))),
    `sortedRegulatoryFeatureConsequences` Nested(consequenceTerms Array(Nullable(Enum8('regulatory_region_ablation' = 0, 'regulatory_region_amplification' = 1, 'regulatory_region_variant' = 2, 'regulatory_region_fusion' = 3))))
)
ENGINE = EmbeddedRocksDB()
PRIMARY KEY key;

CREATE TABLE `GRCh38/SNV_INDEL/variants_memory`
(
    `key` UInt32 CODEC(Delta(8), ZSTD(1)),
    `sortedTranscriptConsequences` Nested(alphamissensePathogenicity Nullable(Decimal(9, 5)), canonical Nullable(UInt8), consequenceTerms Array(Nullable(Enum8('transcript_ablation' = 1, 'splice_acceptor_variant' = 2, 'splice_donor_variant' = 3, 'stop_gained' = 4, 'frameshift_variant' = 5, 'stop_lost' = 6, 'start_lost' = 7, 'inframe_insertion' = 8, 'inframe_deletion' = 9, 'missense_variant' = 10, 'protein_altering_variant' = 11, 'splice_donor_5th_base_variant' = 12, 'splice_region_variant' = 13, 'splice_donor_region_variant' = 14, 'splice_polypyrimidine_tract_variant' = 15, 'incomplete_terminal_codon_variant' = 16, 'start_retained_variant' = 17, 'stop_retained_variant' = 18, 'synonymous_variant' = 19, 'coding_sequence_variant' = 20, 'mature_miRNA_variant' = 21, '5_prime_UTR_variant' = 22, '3_prime_UTR_variant' = 23, 'non_coding_transcript_exon_variant' = 24, 'intron_variant' = 25, 'NMD_transcript_variant' = 26, 'non_coding_transcript_variant' = 27, 'coding_transcript_variant' = 28, 'upstream_gene_variant' = 29, 'downstream_gene_variant' = 30, 'intergenic_variant' = 31, 'sequence_variant' = 32))), extendedIntronicSpliceRegionVariant Nullable(Bool), fiveutrConsequence Nullable(Enum8('5_prime_UTR_premature_start_codon_gain_variant' = 1, '5_prime_UTR_premature_start_codon_loss_variant' = 2, '5_prime_UTR_stop_codon_gain_variant' = 3, '5_prime_UTR_stop_codon_loss_variant' = 4, '5_prime_UTR_uORF_frameshift_variant' = 5)), geneId Nullable(String)),
    `sortedMotifFeatureConsequences` Nested(consequenceTerms Array(Nullable(Enum8('TFBS_ablation' = 0, 'TFBS_amplification' = 1, 'TF_binding_site_variant' = 2, 'TFBS_fusion' = 3, 'TFBS_translocation' = 4)))),
    `sortedRegulatoryFeatureConsequences` Nested(consequenceTerms Array(Nullable(Enum8('regulatory_region_ablation' = 0, 'regulatory_region_amplification' = 1, 'regulatory_region_variant' = 2, 'regulatory_region_fusion' = 3))))
)
ENGINE = EmbeddedRocksDB()
PRIMARY KEY key;

CREATE TABLE `GRCh38/SNV_INDEL/variants/details`
(
    `key` UInt32 CODEC(Delta(8), ZSTD(1)),
    `variantId` String,
    `rsid` Nullable(String),
    `CAID` Nullable(String),
    `liftedOverChrom` Nullable(Enum8('1' = 1, '2' = 2, '3' = 3, '4' = 4, '5' = 5, '6' = 6, '7' = 7, '8' = 8, '9' = 9, '10' = 10, '11' = 11, '12' = 12, '13' = 13, '14' = 14, '15' = 15, '16' = 16, '17' = 17, '18' = 18, '19' = 19, '20' = 20, '21' = 21, '22' = 22, 'X' = 23, 'Y' = 24, 'M' = 25)),
    `liftedOverPos` Nullable(UInt32),
    `transcripts` Nested(alphamissense Tuple(
        pathogenicity Nullable(Decimal(9, 5))), aminoAcids Nullable(String), biotype Nullable(String), canonical Nullable(UInt8), codons Nullable(String), consequenceTerms Array(Nullable(Enum8('transcript_ablation' = 1, 'splice_acceptor_variant' = 2, 'splice_donor_variant' = 3, 'stop_gained' = 4, 'frameshift_variant' = 5, 'stop_lost' = 6, 'start_lost' = 7, 'inframe_insertion' = 8, 'inframe_deletion' = 9, 'missense_variant' = 10, 'protein_altering_variant' = 11, 'splice_donor_5th_base_variant' = 12, 'splice_region_variant' = 13, 'splice_donor_region_variant' = 14, 'splice_polypyrimidine_tract_variant' = 15, 'incomplete_terminal_codon_variant' = 16, 'start_retained_variant' = 17, 'stop_retained_variant' = 18, 'synonymous_variant' = 19, 'coding_sequence_variant' = 20, 'mature_miRNA_variant' = 21, '5_prime_UTR_variant' = 22, '3_prime_UTR_variant' = 23, 'non_coding_transcript_exon_variant' = 24, 'intron_variant' = 25, 'NMD_transcript_variant' = 26, 'non_coding_transcript_variant' = 27, 'coding_transcript_variant' = 28, 'upstream_gene_variant' = 29, 'downstream_gene_variant' = 30, 'intergenic_variant' = 31, 'sequence_variant' = 32))), exon Tuple(
        index Nullable(Int32),
        total Nullable(Int32)), geneId Nullable(String), hgvsc Nullable(String), hgvsp Nullable(String), intron Tuple(
        index Nullable(Int32),
        total Nullable(Int32)), loftee Tuple(
        isLofNagnag Nullable(Bool),
        lofFilters Array(Nullable(String))), majorConsequence Nullable(Enum8('transcript_ablation' = 1, 'splice_acceptor_variant' = 2, 'splice_donor_variant' = 3, 'stop_gained' = 4, 'frameshift_variant' = 5, 'stop_lost' = 6, 'start_lost' = 7, 'inframe_insertion' = 8, 'inframe_deletion' = 9, 'missense_variant' = 10, 'protein_altering_variant' = 11, 'splice_donor_5th_base_variant' = 12, 'splice_region_variant' = 13, 'splice_donor_region_variant' = 14, 'splice_polypyrimidine_tract_variant' = 15, 'incomplete_terminal_codon_variant' = 16, 'start_retained_variant' = 17, 'stop_retained_variant' = 18, 'synonymous_variant' = 19, 'coding_sequence_variant' = 20, 'mature_miRNA_variant' = 21, '5_prime_UTR_variant' = 22, '3_prime_UTR_variant' = 23, 'non_coding_transcript_exon_variant' = 24, 'intron_variant' = 25, 'NMD_transcript_variant' = 26, 'non_coding_transcript_variant' = 27, 'coding_transcript_variant' = 28, 'upstream_gene_variant' = 29, 'downstream_gene_variant' = 30, 'intergenic_variant' = 31, 'sequence_variant' = 32)), manePlusClinical Nullable(String), maneSelect Nullable(String), refseqTranscriptId Nullable(String), spliceregion Tuple(
        extended_intronic_splice_region_variant Nullable(Bool)), transcriptId String, transcriptRank UInt8, utrannotator Tuple(
        existingInframeOorfs Nullable(Int32),
        existingOutofframeOorfs Nullable(Int32),
        existingUorfs Nullable(Int32),
        fiveutrAnnotation Tuple(
            AltStop Nullable(String),
            AltStopDistanceToCDS Nullable(Int32),
            CapDistanceToStart Nullable(Int32),
            DistanceToCDS Nullable(Int32),
            DistanceToStop Nullable(Int32),
            Evidence Nullable(Bool),
            FrameWithCDS Nullable(String),
            KozakContext Nullable(String),
            KozakStrength Nullable(String),
            StartDistanceToCDS Nullable(Int32),
            alt_type Nullable(String),
            alt_type_length Nullable(Int32),
            newSTOPDistanceToCDS Nullable(Int32),
            ref_StartDistanceToCDS Nullable(Int32),
            ref_type Nullable(String),
            ref_type_length Nullable(Int32),
            type Nullable(String)),
        fiveutrConsequence Nullable(String))),
    `sortedMotifFeatureConsequences` Nested(consequenceTerms Array(Nullable(Enum8('TFBS_ablation' = 0, 'TFBS_amplification' = 1, 'TF_binding_site_variant' = 2, 'TFBS_fusion' = 3, 'TFBS_translocation' = 4))), motifFeatureId Nullable(String)),
    `sortedRegulatoryFeatureConsequences` Nested(biotype Nullable(Enum8('enhancer' = 0, 'promoter' = 1, 'CTCF_binding_site' = 2, 'TF_binding_site' = 3, 'open_chromatin_region' = 4)), consequenceTerms Array(Nullable(Enum8('regulatory_region_ablation' = 0, 'regulatory_region_amplification' = 1, 'regulatory_region_variant' = 2, 'regulatory_region_fusion' = 3))), regulatoryFeatureId Nullable(String))
)
ENGINE = EmbeddedRocksDB()
PRIMARY KEY key;

CREATE TABLE `GRCh38/SNV_INDEL/entries`
(
    `key` UInt32 CODEC(Delta(8), ZSTD(1)),
    `project_guid` LowCardinality(String),
    `family_guid` String,
    `sample_type` Enum8('WES' = 1, 'WGS' = 2),
    `xpos` UInt64 CODEC(Delta(8), ZSTD(1)),
    `is_gnomad_gt_5_percent` Bool,
    `is_annotated_in_any_gene` Bool,
    `geneId_ids` Array(UInt32),
    `filters` Array(LowCardinality(String)),
    `calls` Array(Tuple(
        sampleId String,
        gt Nullable(Enum8('REF' = 0, 'HET' = 1, 'HOM' = 2)),
        gq Nullable(UInt8),
        ab Nullable(Decimal(9, 5)),
        dp Nullable(UInt16))),
    `sign` Int8,
    `n_partitions` UInt8 MATERIALIZED dictGetOrDefault('GRCh38/SNV_INDEL/project_partitions_dict', 'n_partitions', project_guid, 1),
    `partition_id` UInt8 MATERIALIZED farmHash64(family_guid) % n_partitions,
    PROJECTION xpos_projection
    (
        SELECT *
        ORDER BY 
            is_gnomad_gt_5_percent,
            is_annotated_in_any_gene,
            xpos
    )
)
ENGINE = CollapsingMergeTree(sign)
PARTITION BY (project_guid, partition_id)
ORDER BY (project_guid, family_guid, sample_type, is_gnomad_gt_5_percent, is_annotated_in_any_gene, key)
SETTINGS deduplicate_merge_projection_mode = 'rebuild', index_granularity = 8192;

CREATE TABLE `GRCh38/SNV_INDEL/gt_stats`
(
    `key` UInt32 CODEC(Delta(8), ZSTD(1)),
    `ac_wes` UInt32,
    `ac_wgs` UInt32,
    `ac_affected` UInt32 DEFAULT 0,
    `hom_wes` UInt32,
    `hom_wgs` UInt32,
    `hom_affected` UInt32 DEFAULT 0
)
ENGINE = SummingMergeTree
ORDER BY key
SETTINGS index_granularity = 8192;

CREATE TABLE `GRCh38/SNV_INDEL/key_lookup`
(
    `variantId` String,
    `key` UInt32 CODEC(Delta(8), ZSTD(1))
)
ENGINE = EmbeddedRocksDB()
PRIMARY KEY variantId;

CREATE TABLE `GRCh38/SNV_INDEL/project_gt_stats`
(
    `project_guid` LowCardinality(String),
    `key` UInt32 CODEC(Delta(8), ZSTD(1)),
    `sample_type` Enum8('WES' = 1, 'WGS' = 2),
    `affected` Enum8('A' = 1, 'N' = 2, 'U' = 3) DEFAULT 'U',
    `ref_samples` UInt32,
    `het_samples` UInt32,
    `hom_samples` UInt32
)
ENGINE = SummingMergeTree
PARTITION BY project_guid
ORDER BY (project_guid, key, sample_type)
SETTINGS index_granularity = 8192;

CREATE TABLE `GRCh38/SNV_INDEL/reference_data/clinvar`
(
    `key` UInt32 CODEC(Delta(8), ZSTD(1)),
    `alleleId` Nullable(UInt32),
    `conflictingPathogenicities` Nested(pathogenicity Enum8('Pathogenic' = 0, 'Pathogenic/Likely_pathogenic' = 1, 'Pathogenic/Likely_pathogenic/Established_risk_allele' = 2, 'Pathogenic/Likely_pathogenic/Likely_risk_allele' = 3, 'Pathogenic/Likely_risk_allele' = 4, 'Likely_pathogenic' = 5, 'Likely_pathogenic/Likely_risk_allele' = 6, 'Established_risk_allele' = 7, 'Likely_risk_allele' = 8, 'Conflicting_classifications_of_pathogenicity' = 9, 'Uncertain_risk_allele' = 10, 'Uncertain_significance/Uncertain_risk_allele' = 11, 'Uncertain_significance' = 12, 'No_pathogenic_assertion' = 13, 'Likely_benign' = 14, 'Benign/Likely_benign' = 15, 'Benign' = 16), count UInt16),
    `goldStars` Nullable(UInt8),
    `submitters` Array(String),
    `conditions` Array(String),
    `assertions` Array(Enum8('Affects' = 0, 'association' = 1, 'association_not_found' = 2, 'confers_sensitivity' = 3, 'drug_response' = 4, 'low_penetrance' = 5, 'not_provided' = 6, 'other' = 7, 'protective' = 8, 'risk_factor' = 9, 'no_classification_for_the_single_variant' = 10, 'no_classifications_from_unflagged_records' = 11)),
    `pathogenicity` Enum8('Pathogenic' = 0, 'Pathogenic/Likely_pathogenic' = 1, 'Pathogenic/Likely_pathogenic/Established_risk_allele' = 2, 'Pathogenic/Likely_pathogenic/Likely_risk_allele' = 3, 'Pathogenic/Likely_risk_allele' = 4, 'Likely_pathogenic' = 5, 'Likely_pathogenic/Likely_risk_allele' = 6, 'Established_risk_allele' = 7, 'Likely_risk_allele' = 8, 'Conflicting_classifications_of_pathogenicity' = 9, 'Uncertain_risk_allele' = 10, 'Uncertain_significance/Uncertain_risk_allele' = 11, 'Uncertain_significance' = 12, 'No_pathogenic_assertion' = 13, 'Likely_benign' = 14, 'Benign/Likely_benign' = 15, 'Benign' = 16)
)
ENGINE = Join(`ALL`, LEFT, key)
SETTINGS join_use_nulls = 1;

CREATE TABLE `GRCh38/SNV_INDEL/reference_data/clinvar/all_variants`
(
    `version` Date,
    `variantId` String,
    `alleleId` Nullable(UInt32),
    `conflictingPathogenicities` Nested(pathogenicity Enum8('Pathogenic' = 0, 'Pathogenic/Likely_pathogenic' = 1, 'Pathogenic/Likely_pathogenic/Established_risk_allele' = 2, 'Pathogenic/Likely_pathogenic/Likely_risk_allele' = 3, 'Pathogenic/Likely_risk_allele' = 4, 'Likely_pathogenic' = 5, 'Likely_pathogenic/Likely_risk_allele' = 6, 'Established_risk_allele' = 7, 'Likely_risk_allele' = 8, 'Conflicting_classifications_of_pathogenicity' = 9, 'Uncertain_risk_allele' = 10, 'Uncertain_significance/Uncertain_risk_allele' = 11, 'Uncertain_significance' = 12, 'No_pathogenic_assertion' = 13, 'Likely_benign' = 14, 'Benign/Likely_benign' = 15, 'Benign' = 16), count UInt16),
    `goldStars` Nullable(UInt8),
    `submitters` Array(String),
    `conditions` Array(String),
    `assertions` Array(Enum8('Affects' = 0, 'association' = 1, 'association_not_found' = 2, 'confers_sensitivity' = 3, 'drug_response' = 4, 'low_penetrance' = 5, 'not_provided' = 6, 'other' = 7, 'protective' = 8, 'risk_factor' = 9, 'no_classification_for_the_single_variant' = 10, 'no_classifications_from_unflagged_records' = 11)),
    `pathogenicity` Enum8('Pathogenic' = 0, 'Pathogenic/Likely_pathogenic' = 1, 'Pathogenic/Likely_pathogenic/Established_risk_allele' = 2, 'Pathogenic/Likely_pathogenic/Likely_risk_allele' = 3, 'Pathogenic/Likely_risk_allele' = 4, 'Likely_pathogenic' = 5, 'Likely_pathogenic/Likely_risk_allele' = 6, 'Established_risk_allele' = 7, 'Likely_risk_allele' = 8, 'Conflicting_classifications_of_pathogenicity' = 9, 'Uncertain_risk_allele' = 10, 'Uncertain_significance/Uncertain_risk_allele' = 11, 'Uncertain_significance' = 12, 'No_pathogenic_assertion' = 13, 'Likely_benign' = 14, 'Benign/Likely_benign' = 15, 'Benign' = 16)
)
ENGINE = MergeTree
PARTITION BY version
PRIMARY KEY (version, variantId)
ORDER BY (version, variantId)
SETTINGS index_granularity = 8192;

CREATE TABLE `GRCh38/SNV_INDEL/reference_data/clinvar/seqr_variants`
(
    `key` UInt32 CODEC(Delta(8), ZSTD(1)),
    `alleleId` Nullable(UInt32),
    `conflictingPathogenicities` Nested(pathogenicity Enum8('Pathogenic' = 0, 'Pathogenic/Likely_pathogenic' = 1, 'Pathogenic/Likely_pathogenic/Established_risk_allele' = 2, 'Pathogenic/Likely_pathogenic/Likely_risk_allele' = 3, 'Pathogenic/Likely_risk_allele' = 4, 'Likely_pathogenic' = 5, 'Likely_pathogenic/Likely_risk_allele' = 6, 'Established_risk_allele' = 7, 'Likely_risk_allele' = 8, 'Conflicting_classifications_of_pathogenicity' = 9, 'Uncertain_risk_allele' = 10, 'Uncertain_significance/Uncertain_risk_allele' = 11, 'Uncertain_significance' = 12, 'No_pathogenic_assertion' = 13, 'Likely_benign' = 14, 'Benign/Likely_benign' = 15, 'Benign' = 16), count UInt16),
    `goldStars` Nullable(UInt8),
    `submitters` Array(String),
    `conditions` Array(String),
    `assertions` Array(Enum8('Affects' = 0, 'association' = 1, 'association_not_found' = 2, 'confers_sensitivity' = 3, 'drug_response' = 4, 'low_penetrance' = 5, 'not_provided' = 6, 'other' = 7, 'protective' = 8, 'risk_factor' = 9, 'no_classification_for_the_single_variant' = 10, 'no_classifications_from_unflagged_records' = 11)),
    `pathogenicity` Enum8('Pathogenic' = 0, 'Pathogenic/Likely_pathogenic' = 1, 'Pathogenic/Likely_pathogenic/Established_risk_allele' = 2, 'Pathogenic/Likely_pathogenic/Likely_risk_allele' = 3, 'Pathogenic/Likely_risk_allele' = 4, 'Likely_pathogenic' = 5, 'Likely_pathogenic/Likely_risk_allele' = 6, 'Established_risk_allele' = 7, 'Likely_risk_allele' = 8, 'Conflicting_classifications_of_pathogenicity' = 9, 'Uncertain_risk_allele' = 10, 'Uncertain_significance/Uncertain_risk_allele' = 11, 'Uncertain_significance' = 12, 'No_pathogenic_assertion' = 13, 'Likely_benign' = 14, 'Benign/Likely_benign' = 15, 'Benign' = 16)
)
ENGINE = MergeTree
PRIMARY KEY key
ORDER BY key
SETTINGS index_granularity = 8192;

CREATE MATERIALIZED VIEW `GRCh38/SNV_INDEL/entries_to_project_gt_stats_mv` TO `GRCh38/SNV_INDEL/project_gt_stats`
(
    `project_guid` LowCardinality(String),
    `key` UInt32,
    `sample_type` Enum8('WES' = 1, 'WGS' = 2),
    `affected` String,
    `ref_samples` Int64,
    `het_samples` Int64,
    `hom_samples` Int64
)
AS SELECT
    project_guid,
    key,
    sample_type,
    dictGetOrDefault('seqrdb_affected_status_dict', 'affected', (family_guid, calls.sampleId), 'U') AS affected,
    sumIf(sign, calls.gt = 'REF') AS ref_samples,
    sumIf(sign, calls.gt = 'HET') AS het_samples,
    sumIf(sign, calls.gt = 'HOM') AS hom_samples
FROM `GRCh38/SNV_INDEL/entries`
ARRAY JOIN calls
GROUP BY
    project_guid,
    key,
    sample_type,
    affected;

CREATE MATERIALIZED VIEW `GRCh38/SNV_INDEL/project_gt_stats_to_gt_stats_mv`
REFRESH EVERY 10 YEAR TO `GRCh38/SNV_INDEL/gt_stats`
(
    `key` UInt32,
    `ac_wes` UInt64,
    `ac_wgs` UInt64,
    `ac_affected` UInt64,
    `hom_wes` UInt64,
    `hom_wgs` UInt64,
    `hom_affected` UInt64
)
AS SELECT
    key,
    sumIf((het_samples * 1) + (hom_samples * 2), sample_type = 'WES') AS ac_wes,
    sumIf((het_samples * 1) + (hom_samples * 2), sample_type = 'WGS') AS ac_wgs,
    sumIf((het_samples * 1) + (hom_samples * 2), affected = 'A') AS ac_affected,
    sumIf(hom_samples, sample_type = 'WES') AS hom_wes,
    sumIf(hom_samples, sample_type = 'WGS') AS hom_wgs,
    sumIf(hom_samples, affected = 'A') AS hom_affected
FROM `GRCh38/SNV_INDEL/project_gt_stats`
WHERE project_guid NOT IN ['R0555_seqr_demo', 'R0607_gregor_training_project_', 'R0608_gregor_training_project_', 'R0801_gregor_training_project_', 'R0811_gregor_training_project_', 'R0812_gregor_training_project_', 'R0813_gregor_training_project_', 'R0814_gregor_training_project_', 'R0815_gregor_training_project_', 'R0816_gregor_training_project_']
GROUP BY key;

CREATE MATERIALIZED VIEW `GRCh38/SNV_INDEL/reference_data/clinvar/all_variants_to_seqr_variants_mv`
REFRESH EVERY 10 YEAR TO `GRCh38/SNV_INDEL/reference_data/clinvar/seqr_variants`
(
    `key` UInt32,
    `alleleId` Nullable(UInt32),
    `conflictingPathogenicities` Nested(pathogenicity Enum8('Pathogenic' = 0, 'Pathogenic/Likely_pathogenic' = 1, 'Pathogenic/Likely_pathogenic/Established_risk_allele' = 2, 'Pathogenic/Likely_pathogenic/Likely_risk_allele' = 3, 'Pathogenic/Likely_risk_allele' = 4, 'Likely_pathogenic' = 5, 'Likely_pathogenic/Likely_risk_allele' = 6, 'Established_risk_allele' = 7, 'Likely_risk_allele' = 8, 'Conflicting_classifications_of_pathogenicity' = 9, 'Uncertain_risk_allele' = 10, 'Uncertain_significance/Uncertain_risk_allele' = 11, 'Uncertain_significance' = 12, 'No_pathogenic_assertion' = 13, 'Likely_benign' = 14, 'Benign/Likely_benign' = 15, 'Benign' = 16), count UInt16),
    `goldStars` Nullable(UInt8),
    `submitters` Array(String),
    `conditions` Array(String),
    `assertions` Array(Enum8('Affects' = 0, 'association' = 1, 'association_not_found' = 2, 'confers_sensitivity' = 3, 'drug_response' = 4, 'low_penetrance' = 5, 'not_provided' = 6, 'other' = 7, 'protective' = 8, 'risk_factor' = 9, 'no_classification_for_the_single_variant' = 10, 'no_classifications_from_unflagged_records' = 11)),
    `pathogenicity` Enum8('Pathogenic' = 0, 'Pathogenic/Likely_pathogenic' = 1, 'Pathogenic/Likely_pathogenic/Established_risk_allele' = 2, 'Pathogenic/Likely_pathogenic/Likely_risk_allele' = 3, 'Pathogenic/Likely_risk_allele' = 4, 'Likely_pathogenic' = 5, 'Likely_pathogenic/Likely_risk_allele' = 6, 'Established_risk_allele' = 7, 'Likely_risk_allele' = 8, 'Conflicting_classifications_of_pathogenicity' = 9, 'Uncertain_risk_allele' = 10, 'Uncertain_significance/Uncertain_risk_allele' = 11, 'Uncertain_significance' = 12, 'No_pathogenic_assertion' = 13, 'Likely_benign' = 14, 'Benign/Likely_benign' = 15, 'Benign' = 16)
)
AS SELECT
    key,
    COLUMNS('.*') EXCEPT (version, variantId, key)
FROM `GRCh38/SNV_INDEL/reference_data/clinvar/all_variants` AS src
INNER JOIN `GRCh38/SNV_INDEL/key_lookup` AS dst ON assumeNotNull(src.variantId) = dst.variantId
LIMIT 1 BY key;


CREATE MATERIALIZED VIEW `GRCh38/SNV_INDEL/reference_data/clinvar/seqr_variants_to_search_mv`
REFRESH EVERY 10 YEAR TO `GRCh38/SNV_INDEL/reference_data/clinvar`
(
    `key` UInt32,
    `alleleId` Nullable(UInt32),
    `conflictingPathogenicities` Nested(pathogenicity Enum8('Pathogenic' = 0, 'Pathogenic/Likely_pathogenic' = 1, 'Pathogenic/Likely_pathogenic/Established_risk_allele' = 2, 'Pathogenic/Likely_pathogenic/Likely_risk_allele' = 3, 'Pathogenic/Likely_risk_allele' = 4, 'Likely_pathogenic' = 5, 'Likely_pathogenic/Likely_risk_allele' = 6, 'Established_risk_allele' = 7, 'Likely_risk_allele' = 8, 'Conflicting_classifications_of_pathogenicity' = 9, 'Uncertain_risk_allele' = 10, 'Uncertain_significance/Uncertain_risk_allele' = 11, 'Uncertain_significance' = 12, 'No_pathogenic_assertion' = 13, 'Likely_benign' = 14, 'Benign/Likely_benign' = 15, 'Benign' = 16), count UInt16),
    `goldStars` Nullable(UInt8),
    `submitters` Array(String),
    `conditions` Array(String),
    `assertions` Array(Enum8('Affects' = 0, 'association' = 1, 'association_not_found' = 2, 'confers_sensitivity' = 3, 'drug_response' = 4, 'low_penetrance' = 5, 'not_provided' = 6, 'other' = 7, 'protective' = 8, 'risk_factor' = 9, 'no_classification_for_the_single_variant' = 10, 'no_classifications_from_unflagged_records' = 11)),
    `pathogenicity` Enum8('Pathogenic' = 0, 'Pathogenic/Likely_pathogenic' = 1, 'Pathogenic/Likely_pathogenic/Established_risk_allele' = 2, 'Pathogenic/Likely_pathogenic/Likely_risk_allele' = 3, 'Pathogenic/Likely_risk_allele' = 4, 'Likely_pathogenic' = 5, 'Likely_pathogenic/Likely_risk_allele' = 6, 'Established_risk_allele' = 7, 'Likely_risk_allele' = 8, 'Conflicting_classifications_of_pathogenicity' = 9, 'Uncertain_risk_allele' = 10, 'Uncertain_significance/Uncertain_risk_allele' = 11, 'Uncertain_significance' = 12, 'No_pathogenic_assertion' = 13, 'Likely_benign' = 14, 'Benign/Likely_benign' = 15, 'Benign' = 16)
)
AS SELECT *
FROM `GRCh38/SNV_INDEL/reference_data/clinvar/seqr_variants`
LIMIT 1 BY key;

