import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'

import { getSavedVariantsIsLoading } from 'redux/selectors'
import { SelectableTableFormInput } from 'shared/components/table/DataTable'
import DataLoader from 'shared/components/DataLoader'
import { ColoredLabel } from 'shared/components/StyledComponents'
import { loadFamilySavedVariants } from '../reducers'

const variantSummary =
  variant => `${variant.chrom}:${variant.pos} ${variant.alt ? `${variant.ref} > ${variant.alt}` : `-${variant.end}`}`

export const GENES_COLUMN = {
  name: 'genes',
  content: 'Genes',
  width: 3,
  format: val => (val.genes || []).map(gene => (gene || {}).geneSymbol).join(', '),
}

export const VARIANT_POS_COLUMN = { name: 'xpos', content: 'Variant', width: 3, format: val => variantSummary(val) }

export const TAG_COLUMN = {
  name: 'tags',
  content: 'Tags',
  width: 8,
  format: val => val.tags.map(
    tag => <ColoredLabel key={tag.tagGuid} size="small" color={tag.color} horizontal content={tag.name} />,
  ),
}

const SelectSavedVariantsTable = React.memo(({ load, loading, familyGuid, dispatch, ...props }) => (
  <DataLoader content contentId={familyGuid} load={load} loading={false}>
    <SelectableTableFormInput defaultSortColumn="xpos" loading={loading} {...props} />
  </DataLoader>
))

SelectSavedVariantsTable.propTypes = {
  load: PropTypes.func,
  loading: PropTypes.bool,
  familyGuid: PropTypes.string,
  dispatch: PropTypes.func,
}

const mapStateToProps = state => ({
  loading: getSavedVariantsIsLoading(state),
})

const mapDispatchToProps = {
  load: loadFamilySavedVariants,
}

export default connect(mapStateToProps, mapDispatchToProps)(SelectSavedVariantsTable)
