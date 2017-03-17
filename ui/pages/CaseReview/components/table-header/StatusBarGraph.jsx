import React from 'react'
import { connect } from 'react-redux'

import { getCaseReviewStatusCounts } from '../../utils/caseReviewStatusCountsSelector'

import { HorizontalSpacer } from '../../../../shared/components/Spacers'
import HorizontalStackedBar from '../../../../shared/components/HorizontalStackedBar'

const StatusBarGraph = props =>
  <span className="nowrap" style={{ float: 'right', paddingRight: '50px' }}>
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
  caseReviewStatusCounts: React.PropTypes.array.isRequired,
}

const mapStateToProps = state => ({
  caseReviewStatusCounts: getCaseReviewStatusCounts(state),
})

export default connect(mapStateToProps)(StatusBarGraph)
