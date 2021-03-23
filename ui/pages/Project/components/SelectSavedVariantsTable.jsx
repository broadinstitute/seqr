import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Icon } from 'semantic-ui-react'

import { getSavedVariantsIsLoading } from 'redux/selectors'
import { SelectableTableFormInput } from 'shared/components/table/DataTable'
import DataLoader from 'shared/components/DataLoader'
import { ColoredLabel } from 'shared/components/StyledComponents'
import { loadFamilySavedVariants } from '../reducers'

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

const SelectSavedVariantsTable = React.memo(({ load, loading, familyGuid, ...props }) =>
  <DataLoader content contentId={familyGuid} load={load} loading={false}>
    <SelectableTableFormInput defaultSortColumn="xpos" loading={loading} {...props} />
  </DataLoader>,
)
// TODO use in matchmaker component
SelectSavedVariantsTable.propTypes = {
  load: PropTypes.func,
  loading: PropTypes.bool,
  familyGuid: PropTypes.string,
}

const mapStateToProps = state => ({
  loading: getSavedVariantsIsLoading(state),
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    load: (contentId) => {
      return dispatch(loadFamilySavedVariants(contentId))
    },
    onChange: newValue => ownProps.onChange(ownProps.data.filter(o => newValue[o[ownProps.idField]])),
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(SelectSavedVariantsTable)
