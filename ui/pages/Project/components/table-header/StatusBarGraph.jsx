/**
import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { HorizontalSpacer } from 'shared/components/Spacers'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'

import { getCaseReviewStatusCounts } from '../../utils/countsSelectors'

const StatusBarGraph = props =>
  <span style={{ whitespace: 'nowrap', float: 'right', paddingRight: '50px' }}>
    <b>Individual Statuses:</b>
    <HorizontalSpacer width={10} />
    <HorizontalStackedBar
      width={100}
      height={10}
      title="Individual Statuses"
      data={props.caseReviewStatusCounts}
    />
  </span>


export { StatusBarGraph as StatusBarGraphComponent }

StatusBarGraph.propTypes = {
  caseReviewStatusCounts: PropTypes.array.isRequired,
}

const mapStateToProps = state => ({
  caseReviewStatusCounts: getCaseReviewStatusCounts(state),
})

export default connect(mapStateToProps)(StatusBarGraph)
*/