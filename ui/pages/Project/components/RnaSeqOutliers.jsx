import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import DataLoader from 'shared/components/DataLoader'
import { loadRnaSeqData } from '../reducers'
import { getRnaSeqDataByIndividual, getRnaSeqDataLoading } from '../selectors'

const BaseRnaSeqOutliers = React.memo(({ sample, rnaSeqData, loading, load }) => (
  <DataLoader content={rnaSeqData} contentId={sample.individualGuid} load={load} loading={loading}>
    {JSON.stringify(rnaSeqData)}
  </DataLoader>
))

BaseRnaSeqOutliers.propTypes = {
  sample: PropTypes.object,
  rnaSeqData: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  rnaSeqData: getRnaSeqDataByIndividual(state)[ownProps.sample.individualGuid],
  loading: getRnaSeqDataLoading(state),
})

const mapDispatchToProps = {
  load: loadRnaSeqData,
}

export default connect(mapStateToProps, mapDispatchToProps)(BaseRnaSeqOutliers)
