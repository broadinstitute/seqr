import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'

import {
  getFamiliesByGuid,
} from 'shared/utils/redux/commonDataActionsAndSelectors'

import {
  setCurrentPage,
  getProjectTablePage,
  getProjectTableRecordsPerPage,
} from '../../redux/rootReducer'

import {
  getTotalPageCount,
  getVisibleFamilyGuids,
} from '../../utils/visibleFamiliesSelector'


const StyledSelect = styled.select`
  max-width: 100px;
  display: inline !important;
  padding: 0px !important;
`

class PageSelector extends React.PureComponent
{
  static propTypes = {
    currentPage: PropTypes.number.isRequired,
    recordsPerPage: PropTypes.number.isRequired,
    totalPageCount: PropTypes.number.isRequired,
    setPage: PropTypes.func.isRequired,
    visibleFamilyGuids: PropTypes.array.isRequired,
    totalFamiliesCount: PropTypes.number.isRequired,
  }

  render() {
    return (
      <div style={{ display: 'inline' }}>
        {
          this.props.totalFamiliesCount > this.props.recordsPerPage ?
            <div style={{ display: 'inline', fontWeight: '400' }}>
              <StyledSelect
                name="familiesFilter"
                value={this.props.currentPage}
                onChange={(e) => {
                  this.props.setPage(parseInt(e.target.value, 10))
                }}
              >
                {
                  [...Array(this.props.totalPageCount).keys()].map(n => (
                    <option key={n + 1} value={n + 1}>
                      {`Page ${n + 1} of ${this.props.totalPageCount}`}
                    </option>
                  ))
                }
              </StyledSelect>
            </div>
            : null
        }
        <div style={{ display: 'inline', fontWeight: '400', paddingLeft: '10px' }}>
          showing &nbsp;
          <b>
            {
              this.props.visibleFamilyGuids.length !== this.props.totalFamiliesCount ?
                `${this.props.visibleFamilyGuids.length} out of ${this.props.totalFamiliesCount}`
                : `all ${this.props.totalFamiliesCount}`
            }
          </b>
          &nbsp; families:
        </div>
      </div>
    )
  }
}

export { PageSelector as PageSelectorComponent }

const mapStateToProps = state => ({
  currentPage: getProjectTablePage(state),
  recordsPerPage: getProjectTableRecordsPerPage(state),
  totalPageCount: getTotalPageCount(state),
  visibleFamilyGuids: getVisibleFamilyGuids(state),
  totalFamiliesCount: Object.keys(getFamiliesByGuid(state)).length,
})

const mapDispatchToProps = {
  setPage: setCurrentPage,
}

export default connect(mapStateToProps, mapDispatchToProps)(PageSelector)
