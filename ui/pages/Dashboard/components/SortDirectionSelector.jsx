import React from 'react'
import { Icon } from 'semantic-ui-react'

const SortDirectionSelector = props =>
  <a
    tabIndex="0"
    style={{ display: 'inline', cursor: 'pointer' }}
    onClick={() => props.onChange(-1 * props.sortDirection)}
  >
    <span style={{ paddingLeft: '10px', paddingRight: '10px' }}>
      {
        props.sortDirection === 1 ?
          <Icon direction="1" name="sort content ascending" /> :
          <Icon direction="-1" name="sort content descending" />
      }
    </span>
  </a>

SortDirectionSelector.propTypes = {
  sortDirection: React.PropTypes.number.isRequired,
  onChange: React.PropTypes.func.isRequired,
}

export default SortDirectionSelector
