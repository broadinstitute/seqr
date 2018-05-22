import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Form } from 'semantic-ui-react'
import styled, { injectGlobal } from 'styled-components'

import { getFamiliesSortOrder, updateFamiliesSortOrder } from '../../../reducers'
import { FAMILY_SORT_OPTIONS } from '../../../constants'

/* eslint-disable no-unused-expressions*/
injectGlobal`
  .inline.field {
    display: inline;
  }
`

const SortLabel = styled.span`
  padding-right: 10px;
`

const SortField = styled(Form.Field)`
  max-width: 150px;
  padding: 0px !important;
`

const SortOrderDropdown = ({
  sortOrder,
  updateSortOrder,
}) =>
  <SortField
    inline
    label={<SortLabel>Sort By: </SortLabel>}
    control="select"
    name="familiesSortOrder"
    value={sortOrder}
    onChange={e => updateSortOrder(e.target.value)}
  >
    {
      FAMILY_SORT_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.name}</option>)
    }
  </SortField>

export { SortOrderDropdown as SortOrderDropdownComponent }


SortOrderDropdown.propTypes = {
  sortOrder: PropTypes.string.isRequired,
  updateSortOrder: PropTypes.func.isRequired,
}

const mapStateToProps = state => ({
  sortOrder: getFamiliesSortOrder(state),
})

const mapDispatchToProps = {
  updateSortOrder: updateFamiliesSortOrder,
}

export default connect(mapStateToProps, mapDispatchToProps)(SortOrderDropdown)
