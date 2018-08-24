import { RadioGroup } from 'shared/components/form/Inputs'

export const CLINVAR_ANNOTATION_GROUPS = [
  {
    name: 'In Clinvar',
    slug: 'clinvar',
    children: [
      'pathogenic',
      'likely_pathogenic',
      'vus_or_conflicting',
      'likely_benign',
      'benign',
    ],
  },
]

export const HGMD_ANNOTATION_GROUPS = [
  {
    name: 'In HGMD',
    slug: 'hgmd',
    children: [ // see https://portal.biobase-international.com/hgmd/pro/global.php#cats
      'disease_causing',
      'likely_disease_causing',
      'hgmd_other',
    ],
  },
]

export const VEP_ANNOTATION_GROUPS = [
  {
    name: 'Nonsense',
    slug: 'nonsense',
    children: [
      'stop_gained',
    ],
  },
  {
    name: 'Essential splice site',
    slug: 'essential_splice_site',
    children: [
      'splice_donor_variant',
      'splice_acceptor_variant',
    ],
  },
  {
    name: 'Extended splice site',
    slug: 'extended_splice_site',
    children: [
      'splice_region_variant',
    ],
  },
  {
    name: 'Missense',
    slug: 'missense',
    children: [
      'stop_lost',
      'initiator_codon_variant',
      'start_lost',
      'missense_variant',
      'protein_altering_variant',
    ],
  },
  {
    name: 'Frameshift',
    slug: 'frameshift',
    children: [
      'frameshift_variant',
    ],
  },
  {
    name: 'In Frame',
    slug: 'inframe',
    children: [
      'inframe_insertion',
      'inframe_deletion',
    ],
  },
  {
    name: 'Synonymous',
    slug: 'synonymous',
    children: [
      'synonymous_variant',
      'stop_retained_variant',
    ],
  },
  {
    name: 'Other',
    slug: 'other',
    children: [
      'transcript_ablation',
      'transcript_amplification',
      'incomplete_terminal_codon_variant',
      'coding_sequence_variant',
      'mature_miRNA_variant',
      '5_prime_UTR_variant',
      '3_prime_UTR_variant',
      'intron_variant',
      'NMD_transcript_variant',
      'non_coding_exon_variant', // 2 kinds of 'non_coding_exon_variant' label due to name change in Ensembl v77
      'non_coding_transcript_exon_variant', // 2 kinds of 'non_coding_exon_variant' due to name change in Ensembl v77
      'nc_transcript_variant', // 2 kinds of 'nc_transcript_variant' label due to name change in Ensembl v77
      'non_coding_transcript_variant', // 2 kinds of 'nc_transcript_variant' due to name change in Ensembl v77
      'upstream_gene_variant',
      'downstream_gene_variant',
      'TFBS_ablation',
      'TFBS_amplification',
      'TF_binding_site_variant',
      'regulatory_region_variant',
      'regulatory_region_ablation',
      'regulatory_region_amplification',
      'feature_elongation',
      'feature_truncation',
      'intergenic_variant',
    ],
  },
]

export const FREQUENCIES = [
  {
    name: '1kg_wgs_phase3',
    label: '1000 Genomes v3',
    homHemi: false,
    labelHelp: 'Filter by allele count (AC) in the 1000 Genomes Phase 3 release (5/2/2013), or by allele frequency (popmax AF) in any one of these five subpopulations defined for 1000 Genomes Phase 3: AFR, AMR, EAS, EUR, SAS',
  },
  {
    name: 'exac_v3',
    label: 'ExAC v0.3',
    homHemi: true,
    labelHelp: 'Filter by allele count (AC) or homozygous/hemizygous count (H/H) in ExAC, or by allele frequency (popmax AF) in any one of these six subpopulations defined for ExAC: AFR, AMR, EAS, FIN, NFE, SAS',
  },
  {
    name: 'gnomad-genomes2',
    label: 'gnomAD 15k genomes',
    homHemi: true,
    labelHelp: 'Filter by allele count (AC) or homozygous/hemizygous count (H/H) among gnomAD genomes, or by allele frequency (popmax AF) in any one of these six subpopulations defined for gnomAD genomes: AFR, AMR, EAS, FIN, NFE, ASJ',
  },
  {
    name: 'gnomad-exomes2',
    label: 'gnomAD 123k exomes',
    homHemi: true,
    labelHelp: 'Filter by allele count (AC) or homozygous/hemizygous count (H/H) among gnomAD exomes, or by allele frequency (popmax AF) in any one of these seven subpopulations defined for gnomAD genomes: AFR, AMR, EAS, FIN, NFE, ASJ, SAS',
  },
  {
    name: 'topmed',
    label: 'TOPMed',
    homHemi: false,
    labelHelp: 'Filter by allele count (AC) or allele frequency (AF) in TOPMed',
  },
  {
    name: 'AF',
    label: 'This Callset',
    homHemi: false,
    labelHelp: 'Filter by allele count (AC) or by allele frequency (AF) among the samples in this family plus the rest of the samples that were joint-called as part of variant calling for this project.',
  },
]

export const QUALITY_FILTER_FIELDS = [
  {
    name: 'vcf_filter',
    label: 'Filter Value',
    labelHelp: 'Either show only variants that PASSed variant quality filters applied when the dataset was processed (typically VQSR or Hard Filters), or show all variants',
    control: RadioGroup,
    options: [{ value: '', text: 'Show All Variants' }, { value: 'pass', text: 'Pass Variants Only' }],
    margin: '1em 2em',
    widths: 'equal',
  },
  {
    name: 'min_gq',
    label: 'Genotype Quality',
    labelHelp: 'Genotype Quality (GQ) is a statistical measure of confidence in the genotype call (eg. hom. or het) based on the read data',
    min: 0,
    max: 100,
  },
  {
    name: 'min_ab',
    label: 'Allele Balance',
    labelHelp: 'The allele balance represents the percentage of reads that support the alt allele out of the total number of sequencing reads overlapping a variant. Use this filter to set a minimum percentage for the allele balance in heterozygous individuals.',
    min: 0,
    max: 50,
  },
]

export const QUALITY_FILTER_OPTIONS = [
  {
    text: 'High Quality',
    value: {
      vcf_filter: 'pass',
      min_gq: 20,
      min_ab: 25,
    },
  },
  {
    text: 'All Passing Variants',
    value: {
      vcf_filter: 'pass',
      min_gq: 0,
      min_ab: 0,
    },
  },
  {
    text: 'All Variants',
    value: {
      vcf_filter: '',
      min_gq: 0,
      min_ab: 0,
    },
  },
].map(({ value, ...option }) => ({ ...option, value: JSON.stringify(value) }))
