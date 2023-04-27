import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Loader, Grid } from 'semantic-ui-react'

import { getGenesById, getRnaSeqDataByIndividual } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import { loadRnaSeqData } from '../reducers'
import { getRnaSeqDataLoading } from '../selectors'

const RnaSeqOutliers = React.lazy(() => import('./RnaSeqOutliers'))
const RnaSeqOutliersTable = React.lazy(() => import('./RnaSeqOutliersTable'))

const OUTLIER_VOLCANO_PLOT_CONFIGS = {
  outliers: {
    getLocation: (({ geneId }) => geneId),
    header: 'OUTRIDER Volcano Plot',
  },
  spliceOutliers: {
    getLocation: (({ chrom, start, end }) => `${chrom}:${start}-${end}`),
    header: 'FRASER Volcano Plot',
  },
}

const BaseRnaSeqResultPage = ({ match, rnaSeqData, genesById, load, loading }) => (
  <DataLoader content={rnaSeqData} contentId={match.params.individualGuid} load={load} loading={loading}>
    <Grid divided>
      <React.Suspense fallback={<Loader />}>
        <Grid.Row columns={rnaSeqData?.spliceOutliers && rnaSeqData?.outliers ? 2 : 1}>
          {Object.entries(rnaSeqData || {}).map(([key, data]) => (
            <Grid.Column key={key}>
              {React.createElement(
                RnaSeqOutliers,
                {
                  familyGuid: match.params.familyGuid,
                  rnaSeqData: data,
                  genesById,
                  getLocation: OUTLIER_VOLCANO_PLOT_CONFIGS[key].getLocation,
                  header: OUTLIER_VOLCANO_PLOT_CONFIGS[key].header,
                },
              )}
            </Grid.Column>
          ))}
        </Grid.Row>
      </React.Suspense>
      {rnaSeqData?.spliceOutliers && (
        <Grid.Row>
          <React.Suspense fallback={<Loader />}>
            {React.createElement(RnaSeqOutliersTable,
              {
                familyGuid: match.params.familyGuid,
                rnaSeqData: rnaSeqData.spliceOutliers,
              })}
          </React.Suspense>
        </Grid.Row>
      )}
    </Grid>
  </DataLoader>
)

BaseRnaSeqResultPage.propTypes = {
  match: PropTypes.object,
  rnaSeqData: PropTypes.object,
  genesById: PropTypes.object,
  load: PropTypes.func,
  loading: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  rnaSeqData: getRnaSeqDataByIndividual(state)[ownProps.match.params.individualGuid],
  genesById: getGenesById(state),
  loading: getRnaSeqDataLoading(state),
})

const mapDispatchToProps = {
  load: loadRnaSeqData,
}

export default connect(mapStateToProps, mapDispatchToProps)(BaseRnaSeqResultPage)
