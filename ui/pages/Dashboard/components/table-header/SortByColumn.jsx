import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { Icon } from 'semantic-ui-react'

import { updateSortColumn, updateSortDirection } from '../../reducers/rootReducer'

const SortByColumn = (props) => {
  const isBeingUsed = props.currentSortColumn === props.sortBy
  return <span style={{ paddingLeft: '5px' }}>
    <a role="button" tabIndex="0"
      onClick={() => {
        if (!isBeingUsed) {
          props.updateSortColumn(props.sortBy)
        } else {
          props.updateSortDirection(-1 * props.sortDirection)
        }
      }}
      className="clickable"
      style={{ marginLeft: '5px', color: '#555555' }}
    >
      {
        (!isBeingUsed && <Icon name="sort" />) ||
        (props.sortDirection !== 1 && <Icon name="sort ascending" />) ||
        <Icon name="sort descending" />
      }
    </a>
  </span>
}

export { SortByColumn as SortByColumnComponent }

SortByColumn.propTypes = {
  currentSortColumn: PropTypes.string.isRequired,
  sortDirection: PropTypes.number.isRequired,
  updateSortColumn: PropTypes.func.isRequired,
  updateSortDirection: PropTypes.func.isRequired,
  sortBy: PropTypes.string.isRequired,
}


const mapStateToProps = state => ({
  currentSortColumn: state.projectsTableState.sortColumn,
  sortDirection: state.projectsTableState.sortDirection,
})

const mapDispatchToProps = {
  updateSortColumn,
  updateSortDirection,
}

export default connect(mapStateToProps, mapDispatchToProps)(SortByColumn)
