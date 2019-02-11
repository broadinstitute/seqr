// TODO move to shared
import { INDIVIDUAL_EXPORT_DATA } from 'pages/Project/constants'

export const CORE_ANVIL_COLUMNS = [{ field: 'Project ID' }].concat(
  INDIVIDUAL_EXPORT_DATA,
  [{ field: 'Causal gene' }],
).map(({ field, header, format }) => (
  { name: field, content: header || field, format: format ? row => format(row[field]) : null }
))

export const VARIANT_ANVIL_COLUMNS = [
  'Zygosity',
  'Chrom',
  'Pos',
  'Ref',
  'Alt',
  'hgvsc',
  'hgvsp',
  'Transcript',
]
