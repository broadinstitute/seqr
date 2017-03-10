import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import { VerticalArrowToggle } from '../../../../shared/components/form/VerticalArrowToggle'
import { getFamiliesSortDirection, updateFamiliesSortDirection } from '../../reducers/rootReducer'


const SortDirectionToggle = ({
  sortDirection,
  updateSortDirection,
}) => <VerticalArrowToggle
  onClick={() => updateSortDirection(-1 * sortDirection)}
  isPointingDown={sortDirection === 1}
/>


SortDirectionToggle.propTypes = {
  sortDirection: React.PropTypes.number.isRequired,
  updateSortDirection: React.PropTypes.func.isRequired,
}


const mapStateToProps = state => ({
  sortDirection: getFamiliesSortDirection(state),
})

const mapDispatchToProps = dispatch => bindActionCreators({
  updateSortDirection: updateFamiliesSortDirection,
}, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(SortDirectionToggle)
