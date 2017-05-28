import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import VerticalArrowToggle from 'shared/components/form/VerticalArrowToggle'
import { getFamiliesSortDirection, updateFamiliesSortDirection } from '../../reducers/rootReducer'


const SortDirectionToggle = ({
  sortDirection,
  updateSortDirection,
}) => <VerticalArrowToggle
  onClick={() => updateSortDirection(-1 * sortDirection)}
  isPointingDown={sortDirection === 1}
/>


export { SortDirectionToggle as SortDirectionToggleComponent }

SortDirectionToggle.propTypes = {
  sortDirection: PropTypes.number.isRequired,
  updateSortDirection: PropTypes.func.isRequired,
}


const mapStateToProps = state => ({
  sortDirection: getFamiliesSortDirection(state),
})

const mapDispatchToProps = {
  updateSortDirection: updateFamiliesSortDirection,
}

export default connect(mapStateToProps, mapDispatchToProps)(SortDirectionToggle)
