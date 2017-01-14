import React from 'react'

import {
  SHOW_ALL,
} from '../constants'


const FilterSelector = props =>
  <div style={{ display: 'inline' }}>
    <span style={{ paddingLeft: '5px', paddingRight: '10px' }}>
      <b>Show Projects:</b>
    </span>
    <select
      name="filterSelector"
      value={props.filter}
      onChange={event => props.onChange(event.target.value)}
      style={{ width: '90px', display: 'inline', padding: '0px !important' }}
    >
      <option value={SHOW_ALL}>All</option>
    </select>
  </div>

FilterSelector.propTypes = {
  filter: React.PropTypes.string.isRequired,
  onChange: React.PropTypes.func.isRequired,
}

export default FilterSelector
