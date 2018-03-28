import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'

import {
  getFamiliesFilter,
  updateFamiliesFilter,
} from '../../reducers'

import {
  FAMILY_FILTER_OPTIONS,
} from '../../constants'

const StyledSelect = styled.select`
  max-width: 170px;
  display: inline !important;
  padding: 0px !important;
`

const FilterDropdown = ({
  familiesFilter,
  updateFilter,
}) =>
  <div style={{ display: 'inline', whiteSpace: 'nowrap', paddingLeft: '10px' }}>
    <StyledSelect
      name="familiesFilter"
      value={familiesFilter}
      onChange={e => updateFilter(e.target.value)}
    >
      {
        FAMILY_FILTER_OPTIONS.map(f => <option key={f.value} value={f.value}>{f.name}</option>)
      }
    </StyledSelect>
  </div>


export { FilterDropdown as FilterDropdownComponent }

FilterDropdown.propTypes = {
  familiesFilter: PropTypes.string.isRequired,
  updateFilter: PropTypes.func.isRequired,
}


const mapStateToProps = state => ({
  familiesFilter: getFamiliesFilter(state),
})

const mapDispatchToProps = {
  updateFilter: updateFamiliesFilter,
}

export default connect(mapStateToProps, mapDispatchToProps)(FilterDropdown)
