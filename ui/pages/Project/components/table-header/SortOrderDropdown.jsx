import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Form } from 'semantic-ui-react'

import { getFamiliesSortOrder, updateFamiliesSortOrder } from '../../redux/rootReducer'

import { FAMILY_SORT_OPTIONS } from '../../constants'


const SortOrderDropdown = ({
  sortOrder,
  updateSortOrder,
}) =>
  <div style={{ display: 'inline' }}>
    <span style={{ paddingRight: '10px' }}><b>Sort By:</b></span>
    <Form.Field
      control="select"
      style={{ maxWidth: '150px', display: 'inline', padding: '0px !important' }}
      name="familiesSortOrder"
      value={sortOrder}
      onChange={e => updateSortOrder(e.target.value)}
    >
      {
        FAMILY_SORT_OPTIONS.map(opt => <option key={opt.value} value={opt.value}>{opt.name}</option>)
      }
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
