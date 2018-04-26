import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'

import { HorizontalSpacer } from 'shared/components/Spacers'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import { CASE_REVIEW_STATUS_OPTIONS } from '../../../constants'
import { getProjectIndividuals } from '../../../reducers'


const StatusBarGraph = ({ individuals }) => {
  const caseReviewStatusCounts = individuals.reduce((acc, individual) => ({
    ...acc, [individual.caseReviewStatus]: (acc[individual.caseReviewStatus] || 0) + 1,
  }), {})

  const caseReviewStatuses = CASE_REVIEW_STATUS_OPTIONS.map(option => (
    { ...option, count: (caseReviewStatusCounts[option.value] || 0) }),
  )

  return (
    <span style={{ whitespace: 'nowrap', float: 'right', paddingRight: '50px' }}>
      <b>Individual Statuses:</b>
      <HorizontalSpacer width={10} />
      <HorizontalStackedBar
        width={100}
        height={10}
        title="Individual Statuses"
        data={caseReviewStatuses}
      />
    </span>
  )
}


export { StatusBarGraph as StatusBarGraphComponent }

StatusBarGraph.propTypes = {
  individuals: PropTypes.array.isRequired,
}

const mapStateToProps = state => ({
  individuals: getProjectIndividuals(state),
})

export default connect(mapStateToProps)(StatusBarGraph)
