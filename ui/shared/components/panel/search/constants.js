import { Form } from 'semantic-ui-react'
import styled from 'styled-components'

import { RadioGroup, InlineToggle } from 'shared/components/form/Inputs'

export const THIS_CALLSET_FREQUENCY = 'callset'
export const SV_CALLSET_FREQUENCY = 'sv_callset'
export const TOPMED_FREQUENCY = 'topmed'
export const SNP_FREQUENCIES = [
  {
    name: 'gnomad_genomes',
    label: 'gnomAD genomes',
    homHemi: true,
    labelHelp: 'Filter by allele count (AC) or homozygous/hemizygous count (H/H) among gnomAD genomes, or by allele frequency (popmax AF) in any one of these five subpopulations defined for gnomAD genomes: AFR, AMR, EAS, NFE, SAS',
  },
  {
    name: 'gnomad_exomes',
    label: 'gnomAD exomes',
    homHemi: true,
    labelHelp: 'Filter by allele count (AC) or homozygous/hemizygous count (H/H) among gnomAD exomes, or by allele frequency (popmax AF) in any one of these five subpopulations defined for gnomAD exomes: AFR, AMR, EAS, NFE, SAS',
  },
  {
    name: TOPMED_FREQUENCY,
    label: 'TOPMed',
    homHemi: false,
    labelHelp: 'Filter by allele count (AC) or allele frequency (AF) in TOPMed',
  },
  {
    name: THIS_CALLSET_FREQUENCY,
    label: 'This Callset',
    homHemi: true,
    labelHelp: 'Filter by allele count (AC) or by allele frequency (AF) among the samples in this family plus the rest of the samples that were joint-called as part of variant calling for this project.',
  },
]

export const MITO_FREQUENCIES = [
  {
    name: 'gnomad_mito',
    label: 'gnomAD homoplasmic',
    homHemi: false,
    labelHelp: 'Filter by the gnomAD allele count (AC) and allele frequency (AF) restricted to variants with a heteroplasmy level >= 0.95',
  },
]

export const SV_CALLSET_CRITERIA_MESSAGE = 'Only an SV that is estimated to be the same SV (type and breakpoints) among jointly genotyped samples will be counted as an allele. CNVs called on exomes have unknown breakpoints so similar overlapping CNVs may be counted as an allele.'
export const GNOMAD_SV_CRITERIA_MESSAGE = 'The following criteria need to be met for an SV in gnomAD to be counted as an allele: Has the same SV type (deletion, duplication, etc) and either has sufficient reciprocal overlap (SVs >5Kb need 50%, SVs < 5Kb need 10%) or has insertion breakpoints within 100bp'
export const SV_FREQUENCIES = [
  {
    name: 'gnomad_svs',
    label: 'gnomAD genome SVs',
    homHemi: false,
    labelHelp: `Filter by locus frequency (AF) among gnomAD SVs. ${GNOMAD_SV_CRITERIA_MESSAGE}`,
  },
  {
    name: SV_CALLSET_FREQUENCY,
    label: 'This SV Callset',
    homHemi: false,
    labelHelp: `Filter by allele count (AC) or by allele frequency (AF) among all the jointly genotyped samples that were part of the Structural Variant (SV) calling for this project. ${SV_CALLSET_CRITERIA_MESSAGE}`,
  },
]

export const FREQUENCIES = [...SNP_FREQUENCIES, ...MITO_FREQUENCIES, ...SV_FREQUENCIES]

export const SNP_QUALITY_FILTER_FIELDS = [
  {
    name: 'affected_only',
    label: 'Affected Only',
    labelHelp: 'Only apply quality filters to affected individuals',
    control: InlineToggle,
    color: 'grey',
    width: 6,
  },
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
    step: 5,
  },
  {
    name: 'min_ab',
    label: 'Allele Balance',
    labelHelp: 'The allele balance represents the percentage of reads that support the alt allele out of the total number of sequencing reads overlapping a variant. Use this filter to set a minimum percentage for the allele balance in heterozygous individuals.',
    min: 0,
    max: 50,
    step: 5,
  },
]

const DividedFormField = styled(Form.Field)`
  border-left: solid grey 1px;
`

export const MITO_QUALITY_FILTER_FIELDS = [
  {
    name: 'min_hl',
    label: 'Heteroplasmy level',
    labelHelp: 'Heteroplasmy level (HL) is the percentage of the alt alleles out of all alleles.',
    min: 0,
    max: 50,
    step: 5,
    component: DividedFormField,
  },
]

export const SV_QUALITY_FILTER_FIELDS = [
  {
    name: 'min_qs',
    label: 'WES SV Quality Score',
    labelHelp: 'The quality score (QS) represents the quality of a Structural Variant call. Recommended SV-QS cutoffs for filtering: duplication >= 50, deletion >= 100, homozygous deletion >= 400.',
    min: 0,
    max: 1000,
    step: 10,
    component: DividedFormField,
  },
  {
    name: 'min_gq_sv',
    label: 'WGS SV Genotype Quality',
    labelHelp: 'The genotype quality (GQ) represents the quality of a Structural Variant call. Recommended SV-GQ cutoffs for filtering: > 10.',
    min: 0,
    max: 100,
    step: 5,
  },
]

export const QUALITY_FILTER_FIELDS = [
  ...SNP_QUALITY_FILTER_FIELDS,
  ...MITO_QUALITY_FILTER_FIELDS,
  ...SV_QUALITY_FILTER_FIELDS,
]

export const ALL_QUALITY_FILTER = {
  text: 'All Variants',
  value: {
    vcf_filter: null,
    min_gq: 0,
    min_ab: 0,
    min_qs: 0,
  },
}

export const QUALITY_FILTER_OPTIONS = [
  ALL_QUALITY_FILTER,
  {
    text: 'High Quality',
    value: {
      vcf_filter: 'pass',
      min_gq: 20,
      min_ab: 25,
      min_qs: 100,
    },
  },
  {
    text: 'All Passing Variants',
    value: {
      vcf_filter: 'pass',
      min_gq: 0,
      min_ab: 0,
      min_qs: 10,
    },
  },
]
