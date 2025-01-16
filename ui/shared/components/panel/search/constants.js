import React from 'react'
import { Form } from 'semantic-ui-react'
import styled from 'styled-components'

import { CreateLocusListButton } from 'shared/components/buttons/LocusListButtons'
import { RadioGroup, AlignedBooleanCheckbox, Select, InlineToggle } from 'shared/components/form/Inputs'
import { snakecaseToTitlecase, camelcaseToTitlecase } from 'shared/utils/stringUtils'
import {
  VEP_GROUP_NONSENSE,
  VEP_GROUP_ESSENTIAL_SPLICE_SITE,
  VEP_GROUP_EXTENDED_SPLICE_SITE,
  VEP_GROUP_MISSENSE,
  VEP_GROUP_FRAMESHIFT,
  VEP_GROUP_INFRAME,
  VEP_GROUP_SYNONYMOUS,
  VEP_GROUP_OTHER,
  VEP_GROUP_SV,
  VEP_GROUP_SV_CONSEQUENCES,
  GROUPED_VEP_CONSEQUENCES,
  LOCUS_LIST_ITEMS_FIELD,
  AFFECTED,
  UNAFFECTED,
  ORDERED_PREDICTOR_FIELDS,
  SPLICE_AI_FIELD,
  VEP_GROUP_SV_NEW,
  PANEL_APP_CONFIDENCE_LEVELS,
  SCREEN_LABELS,
  predictorColorRanges,
} from 'shared/utils/constants'

import LocusListItemsFilter from './LocusListItemsFilter'
import PaMoiSelector from './PaMoiSelector'
import PaLocusListSelector from './PaLocusListSelector'

export const getSelectedAnalysisGroups = (
  analysisGroupsByGuid, familyGuids,
) => Object.values(analysisGroupsByGuid).filter(
  group => group.familyGuids.every(familyGuid => familyGuids.includes(familyGuid)),
)

const REF_REF = 'ref_ref'
const HAS_REF = 'has_ref'
const REF_ALT = 'ref_alt'
const HAS_ALT = 'has_alt'
const ALT_ALT = 'alt_alt'
export const NUM_ALT_OPTIONS = [
  {
    text: '0',
    value: REF_REF,
    description: 'Two ref alleles',
  },
  {
    text: '0-1',
    value: HAS_REF,
    description: 'At least one ref allele',
  },
  {
    text: '1',
    value: REF_ALT,
    description: 'One ref allele and one alt allele',
  },
  {
    text: '1-2',
    value: HAS_ALT,
    description: 'At least one alt allele',
  },
  {
    text: '2',
    value: ALT_ALT,
    description: 'Two alt alleles',
  },
]
export const ALL_INHERITANCE_FILTER = 'all'
const RECESSIVE_FILTER = 'recessive'
const HOM_RECESSIVE_FILTER = 'homozygous_recessive'
const X_LINKED_RECESSIVE_FILTER = 'x_linked_recessive'
const COMPOUND_HET_FILTER = 'compound_het'
const DE_NOVO_FILTER = 'de_novo'
const ANY_AFFECTED = 'any_affected'

export const ALL_RECESSIVE_INHERITANCE_FILTERS = [RECESSIVE_FILTER, COMPOUND_HET_FILTER]

export const INHERITANCE_LOOKUP = {
  [ALL_INHERITANCE_FILTER]: { text: 'All' },
  [RECESSIVE_FILTER]: {
    filter: {
      [AFFECTED]: null,
      [UNAFFECTED]: null,
    },
    text: 'Recessive',
    detail: 'This method identifies genes with any evidence of recessive variation. It is the union of all variants returned by the homozygous recessive, x-linked recessive, and compound heterozygous methods.',
  },
  [HOM_RECESSIVE_FILTER]: {
    filter: {
      [AFFECTED]: ALT_ALT,
      [UNAFFECTED]: HAS_REF,
    },
    color: 'transparent', // Adds an empty label so option is indented
    text: 'Homozygous Recessive',
    detail: 'Finds variants where all affected individuals are Alt / Alt and each of their parents Heterozygous.',
  },
  [X_LINKED_RECESSIVE_FILTER]: {
    filter: {
      [AFFECTED]: ALT_ALT,
      [UNAFFECTED]: HAS_REF,
      mother: REF_ALT,
      father: REF_REF,
    },
    color: 'transparent', // Adds an empty label so option is indented
    text: 'X-Linked Recessive',
    detail: "Recessive inheritance on the X Chromosome. This is similar to the homozygous recessive search, but a proband's father must be homozygous reference. (This is how hemizygous genotypes are called by current variant calling methods.)",
  },
  [DE_NOVO_FILTER]: {
    filter: {
      [AFFECTED]: HAS_ALT,
      [UNAFFECTED]: REF_REF,
    },
    text: 'De Novo/ Dominant',
    detail: 'Finds variants where all affected indivs have at least one alternate allele and all unaffected are homozygous reference.',
  },
  [COMPOUND_HET_FILTER]: {
    filter: {
      [AFFECTED]: REF_ALT,
      [UNAFFECTED]: HAS_REF,
    },
    color: 'transparent', // Adds an empty label so option is indented
    text: 'Compound Heterozygous',
    detail: 'Affected individual(s) have two heterozygous mutations in the same gene on opposite haplotypes. Unaffected individuals cannot have the same combination of alleles as affected individuals, or be homozygous alternate for any of the variants. If parents are not present, this method only searches for pairs of heterozygous variants; they may not be on different haplotypes.',
  },
  [ANY_AFFECTED]: {
    filter: {
      [AFFECTED]: HAS_ALT,
    },
    text: 'Any Affected',
    detail: 'Finds variants where at least one affected individual has at least one alternate allele.',
  },
}

export const INHERITANCE_MODE_LOOKUP = Object.entries(INHERITANCE_LOOKUP).reduce((acc, [mode, { filter }]) => (
  { ...acc, [JSON.stringify(filter)]: mode }), {})

export const INHERITANCE_FILTER_OPTIONS = [
  ALL_INHERITANCE_FILTER, RECESSIVE_FILTER, HOM_RECESSIVE_FILTER, X_LINKED_RECESSIVE_FILTER, COMPOUND_HET_FILTER,
  DE_NOVO_FILTER, ANY_AFFECTED,
].map(value => ({ value, ...INHERITANCE_LOOKUP[value] }))

const CLINVAR_NAME = 'clinvar'
const CLIVAR_PATH = 'pathogenic'
const CLINVAR_LIKELY_PATH = 'likely_pathogenic'
const CLINVAR_UNCERTAIN = 'vus_or_conflicting'
const CLINVAR_OPTIONS = [
  {
    text: 'Pathogenic (P)',
    value: CLIVAR_PATH,
  },
  {
    text: 'Likely Pathogenic (LP)',
    value: CLINVAR_LIKELY_PATH,
  },
  {
    description: 'Clinvar variant of uncertain significance or variant with conflicting interpretations',
    text: 'VUS or Conflicting',
    value: CLINVAR_UNCERTAIN,
  },
  {
    text: 'Likely Benign (LB)',
    value: 'likely_benign',
  },
  {
    text: 'Benign (B)',
    value: 'benign',
  },
]

const HGMD_NAME = 'hgmd'
const HGMD_DM = 'disease_causing'
const HGMD_OPTIONS = [ // see https://portal.biobase-international.com/hgmd/pro/global.php#cats
  {
    description: 'Pathological mutation reported to be disease causing in the corresponding report (i.e. all other HGMD data).',
    text: 'Disease Causing (DM)',
    value: HGMD_DM,
  },
  {
    description: 'Likely pathological mutation reported to be disease causing in the corresponding report, but where the author has indicated that there may be some degree of doubt, or subsequent evidence has come to light in the literature, calling the deleterious nature of the variant into question.',
    text: 'Likely Disease Causing (DM?)',
    value: 'likely_disease_causing',
  },
  {
    description: 'All other classifications present in HGMD (including: Disease-associated polymorphism (DP), Disease-associated polymorphism with additional supporting functional evidence (DFP), In vitro/laboratory or in vivo functional polymorphism (FP), Frameshift or truncating variant (FTV)',
    text: 'Other (DP, DFP, FP, FTV)',
    value: 'hgmd_other',
  },
]

const CLINVAR_FIELD = {
  name: CLINVAR_NAME,
  options: CLINVAR_OPTIONS,
  groupLabel: 'Clinvar',
  width: 1,
}

export const PATHOGENICITY_FIELDS = [
  CLINVAR_FIELD,
]

export const HGMD_PATHOGENICITY_FIELDS = [
  CLINVAR_FIELD,
  {
    name: HGMD_NAME,
    options: HGMD_OPTIONS,
    groupLabel: 'HGMD',
    width: 1,
  },
]

export const ANY_PATHOGENICITY_FILTER = {
  text: 'Any',
  value: {
    [CLINVAR_NAME]: [],
    [HGMD_NAME]: [],
  },
}

export const HGMD_PATHOGENICITY_FILTER_OPTIONS = [
  ANY_PATHOGENICITY_FILTER,
  {
    text: 'Pathogenic/ Likely Path.',
    value: {
      [CLINVAR_NAME]: [CLIVAR_PATH, CLINVAR_LIKELY_PATH],
      [HGMD_NAME]: [HGMD_DM],
    },
  },
  {
    text: 'Not Benign',
    value: {
      [CLINVAR_NAME]: [CLIVAR_PATH, CLINVAR_LIKELY_PATH, CLINVAR_UNCERTAIN],
      [HGMD_NAME]: HGMD_OPTIONS.map(({ value }) => value),
    },
  },
]
export const PATHOGENICITY_FILTER_OPTIONS = HGMD_PATHOGENICITY_FILTER_OPTIONS.map(({ text, value }) => ({
  text, value: { [CLINVAR_NAME]: value[CLINVAR_NAME] },
}))

export const ANNOTATION_GROUPS = Object.entries(GROUPED_VEP_CONSEQUENCES).map(([name, options]) => ({
  name, options, groupLabel: snakecaseToTitlecase(name),
}))

const SCREEN_GROUP = 'SCREEN'
const SCREEN_VALUES = ['PLS', 'pELS', 'dELS', 'DNase-H3K4me3', 'CTCF-only', 'DNase-only', 'low-DNase']
const UTR_ANNOTATOR_GROUP = 'UTRAnnotator'
const UTR_ANNOTATOR_VALUES = [
  'premature_start_codon_gain', 'premature_start_codon_loss', 'stop_codon_gain', 'stop_codon_loss', 'uORF_frameshift',
]
const MOTIF_GROUP = 'motif_feature'
const MOTIF_VALUES = [
  {
    description: 'A feature ablation whereby the deleted region includes a transcription factor binding site',
    text: 'TFBS ablation',
    value: 'TFBS_ablation',
    so: 'SO:0001895',
  },
  {
    description: 'A feature amplification of a region containing a transcription factor binding site',
    text: 'TFBS amplification',
    value: 'TFBS_amplification',
    so: 'SO:0001892',
  },
  {
    description: 'In regulatory region annotated by Ensembl',
    text: 'TF binding site variant',
    value: 'TF_binding_site_variant',
    so: 'SO:0001782',
  },
  {
    description: 'A fusion impacting a transcription factor binding site',
    text: 'TFBS fusion',
    value: 'TFBS_fusion',
  },
  {
    description: 'A translocation impacting a transcription factor binding site',
    text: 'TFBS translocation',
    value: 'TFBS_translocation',
  },
]
const REGULATORY_GROUP = 'regulatory_feature'
const REGULATORY_VALUES = [
  {
    description: 'A sequence variant located within a regulatory region',
    text: 'Regulatory region variant',
    value: 'regulatory_region_variant',
    so: 'SO:0001566',
  },
  {
    description: 'A feature ablation whereby the deleted region includes a regulatory region',
    text: 'Regulatory region ablation',
    value: 'regulatory_region_ablation',
    so: 'SO:0001894',
  },
  {
    description: 'A feature amplification of a region containing a regulatory region',
    text: 'Regulatory region amplification',
    value: 'regulatory_region_amplification',
    so: 'SO:0001891',
  },
  {
    description: 'A fusion impacting a regulatory region',
    text: 'Regulatory region fusion',
    value: 'regulatory_region_fusion',
  },
]
ANNOTATION_GROUPS.push({
  name: SCREEN_GROUP,
  groupLabel: SCREEN_GROUP,
  options: SCREEN_VALUES.map(value => ({
    value,
    text: SCREEN_LABELS[value] || value,
    description: 'SCREEN: Search Candidate cis-Regulatory Elements by ENCODE. Registry of cCREs V3’',
  })),
}, {
  name: UTR_ANNOTATOR_GROUP,
  groupLabel: UTR_ANNOTATOR_GROUP,
  options: UTR_ANNOTATOR_VALUES.map(value => ({
    value: `5_prime_UTR_${value}_variant`,
    text: snakecaseToTitlecase(value),
  })),
}, {
  name: MOTIF_GROUP,
  groupLabel: snakecaseToTitlecase(MOTIF_GROUP),
  options: MOTIF_VALUES,
}, {
  name: REGULATORY_GROUP,
  groupLabel: snakecaseToTitlecase(REGULATORY_GROUP),
  options: REGULATORY_VALUES,
})

const ALL_IMPACT_GROUPS = [
  VEP_GROUP_NONSENSE,
  VEP_GROUP_ESSENTIAL_SPLICE_SITE,
  VEP_GROUP_EXTENDED_SPLICE_SITE,
  VEP_GROUP_MISSENSE,
  VEP_GROUP_FRAMESHIFT,
  VEP_GROUP_INFRAME,
  VEP_GROUP_SYNONYMOUS,
  VEP_GROUP_OTHER,
  VEP_GROUP_SV,
  VEP_GROUP_SV_CONSEQUENCES,
]
const HIGH_IMPACT_GROUPS = [
  VEP_GROUP_NONSENSE,
  VEP_GROUP_ESSENTIAL_SPLICE_SITE,
  VEP_GROUP_FRAMESHIFT,
]
export const ANNOTATION_OVERRIDE_GROUPS = [
  SPLICE_AI_FIELD,
  MOTIF_GROUP,
  REGULATORY_GROUP,
  SCREEN_GROUP,
  UTR_ANNOTATOR_GROUP,
]
export const HIGH_MODERATE_IMPACT_GROUPS = [
  ...HIGH_IMPACT_GROUPS,
  VEP_GROUP_MISSENSE,
  VEP_GROUP_INFRAME,
]
const CODING_IMPACT_GROUPS = [
  VEP_GROUP_SYNONYMOUS,
  VEP_GROUP_EXTENDED_SPLICE_SITE,
]
export const CODING_OTHER_IMPACT_GROUPS = [
  ...CODING_IMPACT_GROUPS,
  VEP_GROUP_OTHER,
]

export const ALL_ANNOTATION_FILTER = {
  text: 'All',
  vepGroups: ALL_IMPACT_GROUPS,
}
export const SV_GROUPS = [VEP_GROUP_SV_CONSEQUENCES, VEP_GROUP_SV, VEP_GROUP_SV_NEW]
export const ANNOTATION_FILTER_OPTIONS = [
  ALL_ANNOTATION_FILTER,
  {
    text: 'High Impact',
    vepGroups: HIGH_IMPACT_GROUPS,
  },
  {
    text: 'Moderate to High Impact',
    vepGroups: HIGH_MODERATE_IMPACT_GROUPS,
  },
  {
    text: 'All rare coding variants',
    vepGroups: HIGH_MODERATE_IMPACT_GROUPS.concat(CODING_IMPACT_GROUPS),
  },
].map(({ vepGroups, ...option }) => ({
  ...option,
  value: vepGroups.reduce((acc, group) => (
    { ...acc, [group]: GROUPED_VEP_CONSEQUENCES[group].map(({ value }) => value) }
  ), {}),
}))
export const ALL_ANNOTATION_FILTER_DETAILS =
  [ALL_ANNOTATION_FILTER].map(({ vepGroups, ...option }) => ({
    ...option,
    value: vepGroups.reduce((acc, group) => (
      { ...acc, [group]: GROUPED_VEP_CONSEQUENCES[group].map(({ value }) => value) }
    ), {}),
  }))[0]

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

export const LOCUS_FIELD_NAME = 'locus'
export const PANEL_APP_FIELD_NAME = 'panelAppItems'
export const SELECTED_MOIS_FIELD_NAME = 'selectedMOIs'
const VARIANT_FIELD_NAME = 'rawVariantItems'
const PANEL_APP_COLORS = [...new Set(
  Object.entries(PANEL_APP_CONFIDENCE_LEVELS).sort((a, b) => b[0] - a[0]).map(config => config[1]),
)]
export const LOCATION_FIELDS = [
  {
    name: LOCUS_LIST_ITEMS_FIELD.name,
    label: LOCUS_LIST_ITEMS_FIELD.label,
    labelHelp: LOCUS_LIST_ITEMS_FIELD.labelHelp,
    component: LocusListItemsFilter,
    width: 9,
    shouldShow: locus => !locus[PANEL_APP_FIELD_NAME],
    shouldDisable: locus => !!locus[VARIANT_FIELD_NAME],
  },
  ...PANEL_APP_COLORS.map(color => ({
    key: color,
    name: `${PANEL_APP_FIELD_NAME}.${color}`,
    iconColor: color,
    label: color === 'none' ? 'Genes' : `${camelcaseToTitlecase(color)} Genes`,
    labelHelp: 'A list of genes, can be separated by commas or whitespace',
    component: LocusListItemsFilter,
    filterComponent: PaLocusListSelector,
    width: 3,
    shouldShow: locus => !!locus[PANEL_APP_FIELD_NAME],
    shouldDisable: locus => !!locus[VARIANT_FIELD_NAME],
    color,
  })),
  {
    name: VARIANT_FIELD_NAME,
    label: 'Variants',
    labelHelp: 'A list of variants. Can be separated by commas or whitespace. Variants can be represented by rsID or in the form <chrom>-<pos>-<ref>-<alt>',
    component: LocusListItemsFilter,
    width: 4,
    shouldDisable: locus => !!locus[LOCUS_LIST_ITEMS_FIELD.name] || !!locus[PANEL_APP_FIELD_NAME],
  },
  {
    name: SELECTED_MOIS_FIELD_NAME,
    label: 'Modes of Inheritance',
    labelHelp: 'Filter the Gene List based on Modes of Inheritance from Panel App',
    component: LocusListItemsFilter,
    filterComponent: PaMoiSelector,
    width: 6,
    shouldDisable: locus => !!locus[VARIANT_FIELD_NAME],
    shouldShow: locus => !!locus[PANEL_APP_FIELD_NAME],
  },
  {
    name: 'create',
    fullFieldValue: true,
    component: LocusListItemsFilter,
    control: CreateLocusListButton,
    width: 4,
    shouldShow: locus => !locus[PANEL_APP_FIELD_NAME],
    shouldDisable: locus => !locus[LOCUS_LIST_ITEMS_FIELD.name],
  },
  {
    name: 'excludeLocations',
    component: LocusListItemsFilter,
    filterComponent: AlignedBooleanCheckbox,
    label: 'Exclude locations',
    labelHelp: 'Search for variants not in the specified genes/ intervals',
    width: 10,
    shouldDisable: locus => !!locus[VARIANT_FIELD_NAME],
  },
]

const REQUIRE_SCORE_FIELD = {
  name: 'requireScore',
  component: AlignedBooleanCheckbox,
  label: 'Require Filtered Predictor',
  labelHelp: 'Only return variants where at least one filtered predictor is present. By default, variants are returned if a predictor meets the filtered value or is missing entirely',
}
export const IN_SILICO_FIELDS = [
  REQUIRE_SCORE_FIELD,
  ...ORDERED_PREDICTOR_FIELDS.filter(({ displayOnly }) => !displayOnly).map(
    ({ field, fieldTitle, thresholds, reverseThresholds, indicatorMap, group, min, max, requiresCitation }) => {
      const label = fieldTitle || snakecaseToTitlecase(field)
      const filterField = { name: field, label, group }

      if (indicatorMap) {
        return {
          labelHelp: `Select a value for ${label}`,
          component: Select,
          options: [
            { text: '', value: null },
            ...Object.entries(indicatorMap).map(([val, { value, ...opt }]) => ({ value: val, text: value, ...opt })),
          ],
          ...filterField,
        }
      }

      const labelHelp = (
        <div>
          {`Enter a numeric cutoff for ${label}`}
          {thresholds && predictorColorRanges(thresholds, requiresCitation, reverseThresholds)}
        </div>
      )
      return {
        labelHelp,
        control: Form.Input,
        type: 'number',
        min: min || 0,
        max: max || 1,
        step: max ? 1 : 0.05,
        ...filterField,
      }
    },
  )]

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
