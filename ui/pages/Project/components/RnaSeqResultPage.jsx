import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Loader, Grid } from 'semantic-ui-react'

import { getGenesById, getSamplesByGuid, getRnaSeqDataByIndividual, getRnaSeqSignificantJunctionData, getIndividualsByGuid } from 'redux/selectors'
import { RNASEQ_JUNCTION_PADDING } from 'shared/utils/constants'
import DataLoader from 'shared/components/DataLoader'
import { loadRnaSeqData } from '../reducers'
import { getRnaSeqDataLoading } from '../selectors'

const RnaSeqOutliers = React.lazy(() => import('./RnaSeqOutliers'))
const RnaSeqOutliersTable = React.lazy(() => import('./RnaSeqJunctionOutliersTable'))

const OUTLIER_VOLCANO_PLOT_CONFIGS = {
  outliers: {
    getLocation: (({ geneId }) => geneId),
    searchType: 'genes',
    title: 'OUTRIDER Outliers',
  },
  spliceOutliers: {
    getLocation: (({ chrom, start, end }) => `${chrom}:${Math.max(1, start - RNASEQ_JUNCTION_PADDING)}-${end + RNASEQ_JUNCTION_PADDING}`),
    searchType: 'regions',
    title: 'FRASER Outliers',
  },
}

const BaseRnaSeqResultPage = (
  { individual, rnaSeqData, significantJunctionOutliers, genesById, samplesByGuid, load, loading },
) => (
  <DataLoader content={rnaSeqData} contentId={individual.individualGuid} load={load} loading={loading}>
    <Grid divided>
      <React.Suspense fallback={<Loader />}>
        <Grid.Row columns={rnaSeqData?.spliceOutliers && rnaSeqData?.outliers ? 2 : 1}>
          {Object.entries(rnaSeqData || {}).map(([key, data]) => (
            <Grid.Column key={key}>
              <RnaSeqOutliers
                familyGuid={individual.familyGuid}
                rnaSeqData={data}
                genesById={genesById}
                samplesByGuid={samplesByGuid}
                {...OUTLIER_VOLCANO_PLOT_CONFIGS[key]}
              />
            </Grid.Column>
          ))}
        </Grid.Row>
      </React.Suspense>
      {significantJunctionOutliers.length && (
        <Grid.Row>
          <React.Suspense fallback={<Loader />}>
            <RnaSeqOutliersTable
              familyGuid={individual.familyGuid}
              data={significantJunctionOutliers}
            />
          </React.Suspense>
        </Grid.Row>
      )}
    </Grid>
  </DataLoader>
)

BaseRnaSeqResultPage.propTypes = {
  individual: PropTypes.object,
  rnaSeqData: PropTypes.object,
  significantJunctionOutliers: PropTypes.arrayOf(PropTypes.object),
  genesById: PropTypes.object,
  samplesByGuid: PropTypes.object,
  load: PropTypes.func,
  loading: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  individual: getIndividualsByGuid(state)[ownProps.match.params.individualGuid],
  rnaSeqData: getRnaSeqDataByIndividual(state)[ownProps.match.params.individualGuid],
  significantJunctionOutliers: getRnaSeqSignificantJunctionData(state)[ownProps.match.params.individualGuid] || [],
  genesById: getGenesById(state),
  samplesByGuid: getSamplesByGuid(state),
  loading: getRnaSeqDataLoading(state),
})

const mapDispatchToProps = {
  load: loadRnaSeqData,
}

export default connect(mapStateToProps, mapDispatchToProps)(BaseRnaSeqResultPage)
