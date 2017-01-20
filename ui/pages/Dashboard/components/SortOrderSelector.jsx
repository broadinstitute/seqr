import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import { updateSortOrder } from '../reducers/projectsTableReducer'

import {
  SORT_BY_PROJECT_NAME,
  SORT_BY_NUM_FAMILIES,
  SORT_BY_NUM_INDIVIDUALS,
  SORT_BY_DATE_CREATED,
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
      <option value={SORT_BY_NUM_FAMILIES}>Family Count</option>
      <option value={SORT_BY_NUM_INDIVIDUALS}>Individual Count</option>
      <option value={SORT_BY_DATE_CREATED}>Date Created</option>
    </select>
  </div>

SortOrderSelector.propTypes = {
  sortOrder: React.PropTypes.string.isRequired,
  onChange: React.PropTypes.func.isRequired,
}

const mapStateToProps = state => ({ sortOrder: state.projectsTable.sortOrder })

const mapDispatchToProps = dispatch => bindActionCreators({ onChange: updateSortOrder }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(SortOrderSelector)
