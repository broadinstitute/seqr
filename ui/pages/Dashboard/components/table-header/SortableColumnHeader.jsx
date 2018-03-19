import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { Icon } from 'semantic-ui-react'

import { updateSortColumn, updateSortDirection } from '../../reducers'

const SortableColumnHeader = (props) => {
  return (
    <span style={{ paddingLeft: '5px' }}>
      <a
        role="button"
        tabIndex="0"
        onClick={() => {
          if (props.currentSortColumn === props.sortBy) {
            props.updateSortDirection(-1 * props.sortDirection)
          } else {
            props.updateSortColumn(props.sortBy)
          }
        }}
        className="clickable"
        style={{ color: '#555555' }}
      >
        <span style={{ marginRight: '5px' }}>
          {props.columnLabel}
        </span>
        {
          (props.currentSortColumn !== props.sortBy && <Icon name="sort" />) ||
          (props.sortDirection !== 1 && <Icon name="sort ascending" />) ||
          <Icon name="sort descending" />
        }
      </a>
    </span>)
}

export { SortableColumnHeader as SortableColumnHeaderComponent }

SortableColumnHeader.propTypes = {
  columnLabel: PropTypes.string.isRequired,
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

export default connect(mapStateToProps, mapDispatchToProps)(SortableColumnHeader)
