import { RadioGroup, BooleanCheckbox, BaseSemanticInput } from 'shared/components/form/Inputs'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'
import {
  VEP_GROUP_NONSENSE,
  VEP_GROUP_ESSENTIAL_SPLICE_SITE,
  VEP_GROUP_EXTENDED_SPLICE_SITE,
  VEP_GROUP_MISSENSE,
  VEP_GROUP_FRAMESHIFT,
  VEP_GROUP_INFRAME,
  VEP_GROUP_SYNONYMOUS,
  GROUPED_VEP_CONSEQUENCES,
  LOCUS_LIST_ITEMS_FIELD,
  AFFECTED,
  UNAFFECTED,
} from 'shared/utils/constants'

export const getSelectedAnalysisGroups = (analysisGroupsByGuid, familyGuids) =>
  Object.values(analysisGroupsByGuid).filter(
    group => group.familyGuids.every(familyGuid => familyGuids.includes(familyGuid)),
  )

export const SEARCH_FORM_NAME = 'variantSearch'

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
}

export const INHERITANCE_MODE_LOOKUP = Object.entries(INHERITANCE_LOOKUP).reduce((acc, [mode, { filter }]) =>
  ({ ...acc, [JSON.stringify(filter)]: mode }), {},
)

export const INHERITANCE_FILTER_OPTIONS = [
  ALL_INHERITANCE_FILTER, RECESSIVE_FILTER, HOM_RECESSIVE_FILTER, X_LINKED_RECESSIVE_FILTER, COMPOUND_HET_FILTER, DE_NOVO_FILTER,
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

export const STAFF_PATHOGENICITY_FIELDS = [
  CLINVAR_FIELD,
  {
    name: HGMD_NAME,
    options: HGMD_OPTIONS,
    groupLabel: 'HGMD',
    width: 1,
  },
]

export const STAFF_PATHOGENICITY_FILTER_OPTIONS = [
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
export const PATHOGENICITY_FILTER_OPTIONS = STAFF_PATHOGENICITY_FILTER_OPTIONS.map(({ text, value }) => ({
  text, value: { [CLINVAR_NAME]: value[CLINVAR_NAME] },
}))

export const ANNOTATION_GROUPS = Object.entries(GROUPED_VEP_CONSEQUENCES).map(([name, options]) => ({
  name, options, groupLabel: snakecaseToTitlecase(name),
}))

export const HIGH_IMPACT_GROUPS = [
  VEP_GROUP_NONSENSE,
  VEP_GROUP_ESSENTIAL_SPLICE_SITE,
  VEP_GROUP_FRAMESHIFT,
]
export const MODERATE_IMPACT_GROUPS = [
  VEP_GROUP_MISSENSE,
  VEP_GROUP_INFRAME,
]
export const CODING_IMPACT_GROUPS = [
  VEP_GROUP_SYNONYMOUS,
  VEP_GROUP_EXTENDED_SPLICE_SITE,
]
export const ANNOTATION_FILTER_OPTIONS = [
  {
    text: 'High Impact',
    vepGroups: HIGH_IMPACT_GROUPS,
  },
  {
    text: 'Moderate to High Impact',
    vepGroups: HIGH_IMPACT_GROUPS.concat(MODERATE_IMPACT_GROUPS),
  },
  {
    text: 'All rare coding variants',
    vepGroups: HIGH_IMPACT_GROUPS.concat(MODERATE_IMPACT_GROUPS).concat(CODING_IMPACT_GROUPS),
  },
].map(({ vepGroups, ...option }) => ({
  ...option,
  value: vepGroups.reduce((acc, group) => (
    { ...acc, [group]: GROUPED_VEP_CONSEQUENCES[group].map(({ value }) => value) }
  ), {}),
}))


export const THIS_CALLSET_FREQUENCY = 'callset'
export const FREQUENCIES = [
  {
    name: 'g1k',
    label: '1000 Genomes v3',
    homHemi: false,
    labelHelp: 'Filter by allele count (AC) in the 1000 Genomes Phase 3 release (5/2/2013), or by allele frequency (popmax AF) in any one of these five subpopulations defined for 1000 Genomes Phase 3: AFR, AMR, EAS, EUR, SAS',
  },
  {
    name: 'exac',
    label: 'ExAC v0.3',
    homHemi: true,
    labelHelp: 'Filter by allele count (AC) or homozygous/hemizygous count (H/H) in ExAC, or by allele frequency (popmax AF) in any one of these six subpopulations defined for ExAC: AFR, AMR, EAS, FIN, NFE, SAS',
  },
  {
    name: 'gnomad_genomes',
    label: 'gnomAD 15k genomes',
    homHemi: true,
    labelHelp: 'Filter by allele count (AC) or homozygous/hemizygous count (H/H) among gnomAD genomes, or by allele frequency (popmax AF) in any one of these six subpopulations defined for gnomAD genomes: AFR, AMR, EAS, FIN, NFE, ASJ',
  },
  {
    name: 'gnomad_exomes',
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
    name: THIS_CALLSET_FREQUENCY,
    label: 'This Callset',
    homHemi: false,
    labelHelp: 'Filter by allele count (AC) or by allele frequency (AF) among the samples in this family plus the rest of the samples that were joint-called as part of variant calling for this project.',
  },
]

export const LOCATION_FIELDS = [
  {
    name: LOCUS_LIST_ITEMS_FIELD.name,
    label: LOCUS_LIST_ITEMS_FIELD.label,
    labelHelp: LOCUS_LIST_ITEMS_FIELD.labelHelp,
    component: BaseSemanticInput,
    inputType: 'TextArea',
    rows: 8,
    width: 7,
  },
  {
    name: 'rawVariantItems',
    label: 'Variants',
    labelHelp: 'A list of variants. Can be separated by commas or whitespace. Variants can be represented by rsID or in the form <chrom>-<pos>-<ref>-<alt>',
    component: BaseSemanticInput,
    inputType: 'TextArea',
    rows: 8,
    width: 4,
  },
  {
    name: 'excludeLocations',
    component: BooleanCheckbox,
    label: 'Exclude locations',
    labelHelp: 'Search for variants not in the specified genes/ intervals',
    width: 3,
  },
]

export const QUALITY_FILTER_FIELDS = [
  {
    name: 'vcf_filter',
    label: 'Filter Value',
    labelHelp: 'Either show only variants that PASSed variant quality filters applied when the dataset was processed (typically VQSR or Hard Filters), or show all variants',
    control: RadioGroup,
    options: [{ value: null, text: 'Show All Variants' }, { value: 'pass', text: 'Pass Variants Only' }],
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
      vcf_filter: null,
      min_gq: 0,
      min_ab: 0,
    },
  },
]
