import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getFamiliesByGuid } from 'shared/utils/redux/commonDataActionsAndSelectors'

import {
  getFamiliesFilter, updateFamiliesFilter,
} from '../../redux/rootReducer'

import { getVisibleFamilyGuids } from '../../utils/visibleFamiliesSelector'

import {
  SHOW_ALL,
  SHOW_IN_REVIEW,
  SHOW_UNCERTAIN,
  SHOW_ACCEPTED,
  SHOW_NOT_ACCEPTED,
  SHOW_MORE_INFO_NEEDED,
  SHOW_NOT_IN_REVIEW,
  SHOW_PENDING_RESULTS_AND_RECORDS,
  SHOW_WAITLIST,
  SHOW_WITHDREW,
  SHOW_INELIGIBLE,
  SHOW_DECLINED_TO_PARTICIPATE,
} from '../../constants'


const FilterDropdown = ({
  familiesFilter,
  filteredCount,
  totalCount,
  updateFilter,
}) =>
  <div style={{ display: 'inline', whiteSpace: 'nowrap' }}>
    <div style={{ display: 'inline-block', minWidth: '150px', paddingRight: '10px' }}>
      <b>
        Showing &nbsp;
        {
          filteredCount !== totalCount ?
            `${filteredCount} of ${totalCount}`
            : totalCount
        }
        &nbsp; families:
      </b>
    </div>
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
      <option value={SHOW_MORE_INFO_NEEDED}>More Info Needed</option>
      <option value={SHOW_NOT_IN_REVIEW}>Not In Review</option>
      <option value={SHOW_PENDING_RESULTS_AND_RECORDS}>Pending Results and Records</option>
      <option value={SHOW_WAITLIST}>Waitlist</option>
      <option value={SHOW_WITHDREW}>Withdrew</option>
      <option value={SHOW_INELIGIBLE}>Ineligible</option>
      <option value={SHOW_DECLINED_TO_PARTICIPATE}>Declined To Participate</option>
    </select>
  </div>


export { FilterDropdown as FilterDropdownComponent }

FilterDropdown.propTypes = {
  familiesFilter: PropTypes.string.isRequired,
  filteredCount: PropTypes.number.isRequired,
  totalCount: PropTypes.number.isRequired,
  updateFilter: PropTypes.func.isRequired,
}


const mapStateToProps = state => ({
  familiesFilter: getFamiliesFilter(state),
  filteredCount: getVisibleFamilyGuids(state).length,
  totalCount: Object.keys(getFamiliesByGuid(state)).length,
})

const mapDispatchToProps = {
  updateFilter: updateFamiliesFilter,
}

export default connect(mapStateToProps, mapDispatchToProps)(FilterDropdown)
