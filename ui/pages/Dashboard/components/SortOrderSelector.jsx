import React from 'react'

import {
  SORT_BY_PROJECT_NAME,
  SORT_BY_DATE_ADDED,
  SORT_BY_DATE_ACCESSED,
} from '../constants'

const SortOrderSelector = props =>
  <div style={{ display: 'inline' }}>
    <span style={{ paddingRight: '10px' }}><b>Sort By:</b></span>
    <select
      name="sortOrder"
      value={props.sortOrder}
      onChange={event => props.onChange(event.target.value)}
      style={{ width: '130px', display: 'inline', padding: '0px !important' }}
    >
      <option value={SORT_BY_PROJECT_NAME}>Project Name</option>
      <option value={SORT_BY_DATE_ADDED}>Date Created</option>
      <option value={SORT_BY_DATE_ACCESSED}>Date Last Accessed</option>
    </select>
  </div>

SortOrderSelector.propTypes = {
  sortOrder: React.PropTypes.string.isRequired,
  onChange: React.PropTypes.func.isRequired,
}

export default SortOrderSelector
