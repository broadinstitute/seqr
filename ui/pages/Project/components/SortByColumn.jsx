import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import { Icon } from 'semantic-ui-react'

import { updateSortColumn, updateSortDirection } from '../reducers/projectsTableReducer'

const SortByColumn = (props) => {
  const isBeingUsed = props.currentSortColumn === props.sortBy
  return <span style={{ paddingLeft: '5px' }}>
    <a
      tabIndex="0"
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

SortByColumn.propTypes = {
  currentSortColumn: React.PropTypes.string.isRequired,
  sortDirection: React.PropTypes.number.isRequired,
  updateSortColumn: React.PropTypes.func.isRequired,
  updateSortDirection: React.PropTypes.func.isRequired,
  sortBy: React.PropTypes.string.isRequired,
}


const mapStateToProps = state => ({
  currentSortColumn: state.projectsTable.sortColumn,
  sortDirection: state.projectsTable.sortDirection,
})

const mapDispatchToProps = dispatch => bindActionCreators({ updateSortColumn, updateSortDirection }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(SortByColumn)
