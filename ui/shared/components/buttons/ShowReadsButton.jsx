import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { updateIgvReadsVisibility } from 'redux/rootReducer'
import { getActiveAlignmentSamplesByFamily } from 'redux/selectors'
import { ButtonLink } from '../StyledComponents'

const ShowReadsButton = ({ numAlignmentSamples, showReads, igvId, familyGuid, ...props }) => (
  numAlignmentSamples ? <ButtonLink icon="options" content="SHOW READS" onClick={showReads} {...props} /> : null
)

ShowReadsButton.propTypes = {
  familyGuid: PropTypes.string.isRequired,
  igvId: PropTypes.string.isRequired,
  numAlignmentSamples: PropTypes.number,
  showReads: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  numAlignmentSamples: (getActiveAlignmentSamplesByFamily(state)[ownProps.familyGuid] || []).length,
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    showReads: () => {
      dispatch(updateIgvReadsVisibility({ [ownProps.igvId]: ownProps.familyGuid }))
    },
  }
}


export default connect(mapStateToProps, mapDispatchToProps)(ShowReadsButton)
