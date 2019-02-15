import React from 'react'
import { Link } from 'react-router-dom'

import { parseHgvs } from 'shared/components/panel/variants/Annotations'
import {
  INDIVIDUAL_FIELD_CONFIGS,
  INDIVIDUAL_HPO_EXPORT_DATA,
  FAMILY_FIELD_CODED_PHENOTYPE,
  FAMILY_FIELD_ID,
  INDIVIDUAL_FIELD_ID,
  INDIVIDUAL_FIELD_PATERNAL_ID,
  INDIVIDUAL_FIELD_MATERNAL_ID,
  INDIVIDUAL_FIELD_SEX,
  INDIVIDUAL_FIELD_AFFECTED,
} from 'shared/utils/constants'

const PROJECT_ID_FIELD = 'Project ID'
const CAUSAL_GENE_FIELD = 'Causal gene'

const FORMAT_FIELDS = {
  [PROJECT_ID_FIELD]: row =>
    <Link to={`/project/${row.projectGuid}/project_page`} target="_blank">{row[PROJECT_ID_FIELD]}</Link>,
  [FAMILY_FIELD_ID]: row =>
    <Link to={`/project/${row.projectGuid}/family_page/${row.familyGuid}`} target="_blank">{row[FAMILY_FIELD_ID]}</Link>,
  [CAUSAL_GENE_FIELD]: row =>
    <Link to={`/project/${row.projectGuid}/saved_variants/family/${row.familyGuid}/Known%20gene%20for%20phenotype`} target="_blank">
      {row[CAUSAL_GENE_FIELD]}
    </Link>,
}

const PROJECT_ID_COL = { name: PROJECT_ID_FIELD }
const CODED_PHENPOTYPE_COL = { name: FAMILY_FIELD_CODED_PHENOTYPE, content: 'Phenotype', style: { minWidth: '200px' } }
const CAUSAL_GENE_COL = { name: CAUSAL_GENE_FIELD }

const INDIVIDUAL_COLUMNS = [
  FAMILY_FIELD_ID,
  INDIVIDUAL_FIELD_ID,
  INDIVIDUAL_FIELD_PATERNAL_ID,
  INDIVIDUAL_FIELD_MATERNAL_ID,
  INDIVIDUAL_FIELD_SEX,
  INDIVIDUAL_FIELD_AFFECTED,
].map((field) => {
  const { label, format } = INDIVIDUAL_FIELD_CONFIGS[field]
  return {
    name: field,
    content: label,
    format: format ? row => format(row[field]) : null,
  }
})

const HPO_COLUMNS = INDIVIDUAL_HPO_EXPORT_DATA.map(({ field, header, format }) => (
  { name: header, content: header, format: row => format(row[field]), style: { minWidth: '400px' } }
))

export const CORE_ANVIL_COLUMNS = [
  PROJECT_ID_COL, ...INDIVIDUAL_COLUMNS, CODED_PHENPOTYPE_COL, ...HPO_COLUMNS, CAUSAL_GENE_COL,
].map(({ name, content, format, ...props }) => ({
  name,
  content: content || name,
  format: format || FORMAT_FIELDS[name],
  noFormatExport: Boolean(FORMAT_FIELDS[name]),
  ...props,
}))

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
