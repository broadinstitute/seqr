import React from 'react'
import PropTypes from 'prop-types'
import { Icon } from 'semantic-ui-react'

import { SelectableTableFormInput } from 'shared/components/table/DataTable'
import DataLoader from 'shared/components/DataLoader'
import { ColoredLabel } from 'shared/components/StyledComponents'

const variantSummary = variant => (
  <span>
    {variant.chrom}:{variant.pos}
    {variant.alt ? <span> {variant.ref} <Icon fitted name="angle right" /> {variant.alt}</span> : `-${variant.end}`}
  </span>
)

export const VARIANT_POS_COLUMN = { name: 'xpos', content: 'Variant', width: 3, format: val => variantSummary(val) }

export const TAG_COLUMN = {
  name: 'tags',
  content: 'Tags',
  width: 8,
  format: val => val.tags.map(tag =>
    <ColoredLabel key={tag.tagGuid}size="small" color={tag.color} horizontal content={tag.name} />,
  ),
}

const SelectSavedVariantsTable = React.memo(({ savedVariants, load, loading, familyGuid, idField, columns, value, onChange }) =>
  <DataLoader content contentId={familyGuid} load={load} loading={false}>
    <SelectableTableFormInput
      idField={idField}
      defaultSortColumn="xpos"
      columns={columns}
      data={savedVariants}
      value={value}
      onChange={newValue => onChange(savedVariants.filter(variant => newValue[variant[idField]]))}
      loading={loading}
    />
  </DataLoader>,
)
// TODO use in matchmaker component
SelectSavedVariantsTable.propTypes = {
  savedVariants: PropTypes.array,
  value: PropTypes.object,
  load: PropTypes.func,
  loading: PropTypes.bool,
  familyGuid: PropTypes.string,
  idField: PropTypes.string,
  columns: PropTypes.array,
  onChange: PropTypes.func,
}

export default SelectSavedVariantsTable
