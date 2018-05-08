import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Form } from 'semantic-ui-react'
import { injectGlobal } from 'styled-components'

import { getFamiliesSortOrder, updateFamiliesSortOrder } from '../../../reducers'
import { FAMILY_SORT_OPTIONS } from '../../../constants'

/* eslint-disable no-unused-expressions*/
injectGlobal`
  .inline.field {
    display: inline;
  }
`

const SortOrderDropdown = ({
  sortOrder,
  updateSortOrder,
}) =>
  <Form.Field
    inline
    label={<span style={{ paddingRight: '10px' }}>Sort By: </span>}
    control="select"
    style={{ maxWidth: '150px', padding: '0px !important' }}
    name="familiesSortOrder"
    value={sortOrder}
    onChange={e => updateSortOrder(e.target.value)}
  >
    {
      FAMILY_SORT_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.name}</option>)
    }
  </Form.Field>

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
