import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { getFamiliesByGuid } from 'shared/utils/commonSelectors'

import {
  getFamiliesFilter,
  updateFamiliesFilter,
} from '../../reducers/rootReducer'

import { getVisibleFamilyGuids } from '../../utils/visibleFamiliesSelector'

import {
  FAMILY_FILTER_OPTIONS,
} from '../../constants'


const FilterDropdown = ({
  familiesFilter,
  filteredCount,
  totalCount,
  updateFilter,
}) =>
  <div style={{ display: 'inline', whiteSpace: 'nowrap' }}>
    <div style={{ display: 'inline-block', minWidth: '150pt', paddingLeft: '5px', paddingRight: '10px' }}>
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
      style={{ maxWidth: '170px', display: 'inline', padding: '0px !important' }}
      name="familiesFilter"
      value={familiesFilter}
      onChange={e => updateFilter(e.target.value)}
    >
      {
        FAMILY_FILTER_OPTIONS.map(f => <option key={f.value} value={f.value}>{f.name}</option>)
      }
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
