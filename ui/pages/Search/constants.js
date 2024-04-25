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
