import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Loader, Grid } from 'semantic-ui-react'

import { getGenesById, getRnaSeqDataByIndividual } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import { loadRnaSeqData } from '../reducers'
import { getRnaSeqDataLoading } from '../selectors'

const RnaSeqOutliers = React.lazy(() => import('./RnaSeqOutliers'))
const RnaSeqSpliceOutliers = React.lazy(() => import('./RnaSeqSpliceOutliers'))
const RnaSeqOutliersTable = React.lazy(() => import('./RnaSeqOutliersTable'))

const BaseRnaSeqResultPage = ({ match, rnaSeqData, genesById, load, loading }) => (
  <DataLoader content={rnaSeqData} contentId={match.params.individualGuid} load={load} loading={loading}>
    <Grid divided>
      <Grid.Row columns={rnaSeqData?.spliceOutliers && rnaSeqData?.outliers ? 2 : 1}>
        {rnaSeqData?.outliers && (
          <Grid.Column>
            <React.Suspense fallback={<Loader />}>
              {React.createElement(
                RnaSeqOutliers,
                {
                  familyGuid: match.params.familyGuid,
                  individualGuid: match.params.individualGuid,
                  rnaSeqData: rnaSeqData.outliers,
                  genesById,
                },
              )}
            </React.Suspense>
          </Grid.Column>
        )}
        {rnaSeqData?.spliceOutliers && (
          <Grid.Column>
            <React.Suspense fallback={<Loader />}>
              {React.createElement(
                RnaSeqSpliceOutliers,
                {
                  familyGuid: match.params.familyGuid,
                  individualGuid: match.params.individualGuid,
                  rnaSeqData: rnaSeqData.spliceOutliers,
                  genesById,
                },
              )}
            </React.Suspense>
          </Grid.Column>
        )}
      </Grid.Row>
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
