import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import {
  getFamiliesByGuid,
  getFamiliesFilter,
  updateFamiliesFilter,
} from '../../reducers/rootReducer'

import { getVisibleFamilyGuids } from '../../utils/visibleFamiliesSelector'

import {
  SHOW_ALL,
  SHOW_IN_REVIEW,
  SHOW_UNCERTAIN,
  SHOW_ACCEPTED,
  SHOW_NOT_ACCEPTED,
  SHOW_HOLD,
  SHOW_MORE_INFO_NEEDED,
} from '../../constants'


const FamiliesFilterDropdown = ({
  familiesFilter,
  filteredCount,
  totalCount,
  updateFilter,
}) =>
  <div style={{ display: 'inline', whiteSpace: 'nowrap' }}>
    <span style={{ paddingLeft: '5px', paddingRight: '10px' }}>
      <b>
        Showing &nbsp;
        {
          filteredCount !== totalCount ?
            `${filteredCount} of ${totalCount}`
            : totalCount
        }
        &nbsp; families:
      </b>
    </span>
    <select
      style={{ maxWidth: '137px', display: 'inline', padding: '0px !important' }}
      name="familiesFilter"
      value={familiesFilter}
      onChange={e => updateFilter(e.target.value)}
    >
      <option value={SHOW_ALL}>All</option>
      <option value={SHOW_IN_REVIEW}>In Review</option>
      <option value={SHOW_UNCERTAIN}>Uncertain</option>
      <option value={SHOW_ACCEPTED}>Accepted</option>
      <option value={SHOW_NOT_ACCEPTED}>Not Accepted</option>
      <option value={SHOW_HOLD}>Hold</option>
      <option value={SHOW_MORE_INFO_NEEDED}>More Info Needed</option>
    </select>
  </div>


FamiliesFilterDropdown.propTypes = {
  familiesFilter: React.PropTypes.string.isRequired,
  filteredCount: React.PropTypes.number.isRequired,
  totalCount: React.PropTypes.number.isRequired,
  updateFilter: React.PropTypes.func.isRequired,
}


const mapStateToProps = state => ({
  familiesFilter: getFamiliesFilter(state),
  filteredCount: getVisibleFamilyGuids(state).length,
  totalCount: Object.keys(getFamiliesByGuid(state)).length,
})

const mapDispatchToProps = dispatch => bindActionCreators({
  updateFilter: updateFamiliesFilter,
}, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(FamiliesFilterDropdown)
