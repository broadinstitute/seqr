// TODO move to shared
import { INDIVIDUAL_FIELDS, INDIVIDUAL_FIELD_CONFIGS, INDIVIDUAL_HPO_EXPORT_DATA } from 'pages/Project/constants'

import { parseHgvs } from 'shared/components/panel/variants/Annotations'

export const CORE_ANVIL_COLUMNS = [{ name: 'Project ID', content: 'Project ID' }].concat(
  INDIVIDUAL_FIELDS.map(({ name, content }) => ({
    name,
    content,
    format: INDIVIDUAL_FIELD_CONFIGS[name].format ? row => INDIVIDUAL_FIELD_CONFIGS[name].format(row[name]) : null,
  })),
  [{ name: 'codedPhenotype', content: 'Phenotype', style: { minWidth: '200px' } }],
  INDIVIDUAL_HPO_EXPORT_DATA.map(({ field, header, format }) => (
    { name: header, content: header, format: row => format(row[field]), style: { minWidth: '400px' } }
  )),
  [{ name: 'Causal gene', content: 'Causal gene' }],
)

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

export const VARIANT_ANVIL_COLUMN_FORMATS = {
  hgvsc: parseHgvs,
  hgvsp: parseHgvs,
}
