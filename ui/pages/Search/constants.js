import {
  AFFECTED, UNAFFECTED, RECESSIVE_FILTER, HOM_RECESSIVE_FILTER, X_LINKED_RECESSIVE_FILTER, COMPOUND_HET_FILTER,
  DE_NOVO_FILTER, ANY_AFFECTED, INHERITANCE_FILTER_OPTIONS,
} from 'shared/utils/constants'

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

export const ALL_RECESSIVE_INHERITANCE_FILTERS = [RECESSIVE_FILTER, COMPOUND_HET_FILTER]

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
