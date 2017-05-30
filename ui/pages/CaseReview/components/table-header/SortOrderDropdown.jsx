import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Form } from 'semantic-ui-react'

import { getFamiliesSortOrder, updateFamiliesSortOrder } from '../../reducers/rootReducer'

import {
  SORT_BY_FAMILY_NAME,
  SORT_BY_DATE_ADDED,
  SORT_BY_DATE_LAST_CHANGED,
} from '../../constants'


const SortOrderDropdown = ({
  sortOrder,
  updateSortOrder,
}) =>
  <div style={{ display: 'inline' }}>
    <span style={{ paddingRight: '10px' }}><b>Sort By:</b></span>
    <Form.Field
      control="select"
      style={{ maxWidth: '130px', display: 'inline', padding: '0px !important' }}
      name="familiesSortOrder"
      value={sortOrder}
      onChange={e => updateSortOrder(e.target.value)}
    >
      <option value={SORT_BY_FAMILY_NAME}>Family Name</option>
      <option value={SORT_BY_DATE_ADDED}>Date Added</option>
      <option value={SORT_BY_DATE_LAST_CHANGED}>Last Changed</option>
    </Form.Field>
  </div>

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
