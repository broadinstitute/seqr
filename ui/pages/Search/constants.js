import {
  AFFECTED,
  UNAFFECTED,
  ANY_AFFECTED,
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
  VEP_GROUP_SV_NEW,
  GROUPED_VEP_CONSEQUENCES,
  SPLICE_AI_FIELD,
  SCREEN_LABELS,
} from 'shared/utils/constants'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'

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
export const ALL_RECESSIVE_INHERITANCE_FILTERS = [RECESSIVE_FILTER, COMPOUND_HET_FILTER]

const INHERITANCE_FILTER_OPTIONS = [
  { value: ALL_INHERITANCE_FILTER, text: 'All' },
  {
    value: RECESSIVE_FILTER,
    text: 'Recessive',
    detail: 'This method identifies genes with any evidence of recessive variation. It is the union of all variants returned by the homozygous recessive, x-linked recessive, and compound heterozygous methods.',
  },
  {
    value: HOM_RECESSIVE_FILTER,
    color: 'transparent', // Adds an empty label so option is indented
    text: 'Homozygous Recessive',
    detail: 'Finds variants where all affected individuals are Alt / Alt and each of their parents Heterozygous.',
  },
  {
    value: X_LINKED_RECESSIVE_FILTER,
    color: 'transparent', // Adds an empty label so option is indented
    text: 'X-Linked Recessive',
    detail: "Recessive inheritance on the X Chromosome. This is similar to the homozygous recessive search, but a proband's father must be homozygous reference. (This is how hemizygous genotypes are called by current variant calling methods.)",
  },
  {
    value: COMPOUND_HET_FILTER,
    color: 'transparent', // Adds an empty label so option is indented
    text: 'Compound Heterozygous',
    detail: 'Affected individual(s) have two heterozygous mutations in the same gene on opposite haplotypes. Unaffected individuals cannot have the same combination of alleles as affected individuals, or be homozygous alternate for any of the variants. If parents are not present, this method only searches for pairs of heterozygous variants; they may not be on different haplotypes.',
  },
  {
    value: DE_NOVO_FILTER,
    text: 'De Novo/ Dominant',
    detail: 'Finds variants where all affected individuals have at least one alternate allele and all unaffected are homozygous reference.',
  },
  {
    value: ANY_AFFECTED,
    text: 'Any Affected',
    detail: 'Finds variants where at least one affected individual has at least one alternate allele.',
  },
]

export const INHERITANCE_FILTER_LOOKUP = {
  [RECESSIVE_FILTER]: {
    [AFFECTED]: null,
    [UNAFFECTED]: null,
  },
  [HOM_RECESSIVE_FILTER]: {
    [AFFECTED]: ALT_ALT,
    [UNAFFECTED]: HAS_REF,
  },
  [X_LINKED_RECESSIVE_FILTER]: {
    [AFFECTED]: ALT_ALT,
    [UNAFFECTED]: HAS_REF,
    father: REF_REF,
  },
  [DE_NOVO_FILTER]: {
    [AFFECTED]: HAS_ALT,
    [UNAFFECTED]: REF_REF,
  },
  [COMPOUND_HET_FILTER]: {
    [AFFECTED]: REF_ALT,
    [UNAFFECTED]: HAS_REF,
  },
  [ANY_AFFECTED]: {
    [AFFECTED]: HAS_ALT,
  },
}

export const INHERITANCE_MODE_LOOKUP = Object.entries(INHERITANCE_FILTER_LOOKUP).reduce(
  (acc, [mode, filter]) => ({ ...acc, [mode]: mode, [JSON.stringify(filter)]: mode }), {},
)

export const INHERITANCE_FILTER_JSON_OPTIONS = INHERITANCE_FILTER_OPTIONS.map(
  opt => ({ ...opt, filter: INHERITANCE_FILTER_LOOKUP[opt.value] }),
)

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

export const CLINVAR_FIELD = {
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

const HIGH_IMPACT_GROUPS = [
  VEP_GROUP_NONSENSE,
  VEP_GROUP_ESSENTIAL_SPLICE_SITE,
  VEP_GROUP_FRAMESHIFT,
]
const VEP_OVERRIDE_GROUPS = [
  MOTIF_GROUP,
  REGULATORY_GROUP,
]
const ANNOTATION_OVERRIDE_GROUPS = [
  SPLICE_AI_FIELD,
  ...VEP_OVERRIDE_GROUPS,
  SCREEN_GROUP,
  UTR_ANNOTATOR_GROUP,
]
const HIGH_MODERATE_IMPACT_GROUPS = [
  ...HIGH_IMPACT_GROUPS,
  VEP_GROUP_MISSENSE,
  VEP_GROUP_INFRAME,
]
const CODING_IMPACT_GROUPS = [
  VEP_GROUP_SYNONYMOUS,
  VEP_GROUP_EXTENDED_SPLICE_SITE,
]
const CODING_OTHER_IMPACT_GROUPS = [
  ...CODING_IMPACT_GROUPS,
  VEP_GROUP_OTHER,
]

const NO_OVERRIDE_IMPACT_GROUPS = [HIGH_MODERATE_IMPACT_GROUPS, CODING_OTHER_IMPACT_GROUPS]
export const ALL_CODING_IMPACT_GROUPS = [...NO_OVERRIDE_IMPACT_GROUPS, VEP_OVERRIDE_GROUPS]

export const VARIANT_ANNOTATION_LAYOUT_GROUPS = [
  ...NO_OVERRIDE_IMPACT_GROUPS, ANNOTATION_OVERRIDE_GROUPS,
]

const ALL_ANNOTATION_FILTER = {
  text: 'All',
  vepGroups: [],
}
export const SV_GROUPS_NO_NEW = [VEP_GROUP_SV_CONSEQUENCES, VEP_GROUP_SV]
export const SV_GROUPS = [...SV_GROUPS_NO_NEW, VEP_GROUP_SV_NEW]
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

export const LOCUS_FIELD_NAME = 'locus'
export const PANEL_APP_FIELD_NAME = 'panelAppItems'

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
