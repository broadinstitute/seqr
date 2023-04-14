import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getGenesById, getRnaSeqDataByIndividual } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import { GeneSearchLink } from 'shared/components/buttons/SearchResultsLink'
import { loadRnaSeqData } from '../reducers'
import { getRnaSeqDataLoading } from '../selectors'
import RnaSeqOutlierVolcanoPlot from './RnaSeqOutlierVolcanoPlot'

const BaseRnaSeqOutliers = React.memo(({ individualGuid, rnaSeqData, genesById, familyGuid, loading, load }) => (
  <DataLoader content={rnaSeqData} contentId={individualGuid} load={load} loading={loading}>
    <GeneSearchLink
      buttonText="Search for variants in outlier genes"
      icon="search"
      location={Object.values(rnaSeqData || {}).filter(({ isSignificant }) => isSignificant).map(({ geneId }) => geneId).join(',')}
      familyGuid={familyGuid}
      floated="right"
    />
    <RnaSeqOutlierVolcanoPlot data={rnaSeqData} genesById={genesById} />
  </DataLoader>
))

BaseRnaSeqOutliers.propTypes = {
  individualGuid: PropTypes.string.isRequired,
  familyGuid: PropTypes.string.isRequired,
  rnaSeqData: PropTypes.object,
  genesById: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  rnaSeqData: getRnaSeqDataByIndividual(state)[ownProps.individualGuid]?.outliers,
  genesById: getGenesById(state),
  loading: getRnaSeqDataLoading(state),
})

const mapDispatchToProps = {
  load: loadRnaSeqData,
}

export default connect(mapStateToProps, mapDispatchToProps)(BaseRnaSeqOutliers)
