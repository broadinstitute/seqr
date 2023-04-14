import React from 'react'
import PropTypes from 'prop-types'
import { Loader, Grid } from 'semantic-ui-react'

const RnaSeqOutliers = React.lazy(() => import('./RnaSeqOutliers'))
const RnaSeqSpliceOutliers = React.lazy(() => import('./RnaSeqSpliceOutliers'))

const RnaSeqResultPage = ({ match }) => (
  <Grid>
    {match.params.hasRnaOutlierData === 'true' && (
      <Grid.Row>
        <Grid.Column width={6}>
          <React.Suspense fallback={<Loader />}>
            {React.createElement(RnaSeqOutliers,
              { familyGuid: match.params.familyGuid, individualGuid: match.params.individualGuid }) }
          </React.Suspense>
        </Grid.Column>
      </Grid.Row>
    )}
    {match.params.hasRnaSpliceOutlierData === 'true' && (
      <Grid.Row>
        <React.Suspense fallback={<Loader />}>
          {React.createElement(RnaSeqSpliceOutliers,
            { familyGuid: match.params.familyGuid, individualGuid: match.params.individualGuid }) }
        </React.Suspense>
      </Grid.Row>
    )}
  </Grid>
)

RnaSeqResultPage.propTypes = {
  match: PropTypes.object,
}

export default RnaSeqResultPage
