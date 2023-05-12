import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Loader, Grid, Dropdown } from 'semantic-ui-react'

import { getGenesById, getSamplesByGuid, getIndividualsByGuid, getRnaSeqDataByIndividual } from 'redux/selectors'
import { RNASEQ_JUNCTION_PADDING, TISSUE_DISPLAY } from 'shared/utils/constants'
import DataLoader from 'shared/components/DataLoader'
import { loadRnaSeqData } from '../reducers'
import { getRnaSeqDataLoading, getRnaSeqSignificantJunctionData } from '../selectors'

const RnaSeqOutliers = React.lazy(() => import('./RnaSeqOutliers'))
const RnaSeqOutliersTable = React.lazy(() => import('./RnaSeqJunctionOutliersTable'))

const OUTLIER_VOLCANO_PLOT_CONFIGS = {
  outliers: {
    getLocation: (({ geneId }) => geneId),
    searchType: 'genes',
    title: 'Expression Outliers',
    formatData: ({ data }) => data,
  },
  spliceOutliers: {
    getLocation: (({ chrom, start, end }) => `${chrom}:${Math.max(1, start - RNASEQ_JUNCTION_PADDING)}-${end + RNASEQ_JUNCTION_PADDING}`),
    searchType: 'regions',
    title: 'Splice Junction Outliers',
    formatData: ({ data, sampleGuid }) => data.filter(outlier => outlier.sampleGuid === sampleGuid),
  },
}

class BaseRnaSeqResultPage extends React.PureComponent {

  static propTypes = {
    individual: PropTypes.object,
    rnaSeqData: PropTypes.object,
    significantJunctionOutliers: PropTypes.arrayOf(PropTypes.object),
    genesById: PropTypes.object,
    samplesByGuid: PropTypes.object,
  }

  state = {
    sampleGuid: null,
    tissueOptions: null,
  }

  componentDidMount() {
    const tissueOptions = this.getTissueOptions()
    if (tissueOptions.length) {
      this.setState({ sampleGuid: tissueOptions[0].value, tissueOptions })
    }
  }

  getTissueOptions = () => {
    const { rnaSeqData, samplesByGuid } = this.props
    const sampleGuids = Object.values(rnaSeqData?.spliceOutliers || {}).flat().reduce(
      (acc, { sampleGuid }) => acc.add(sampleGuid), new Set(),
    )
    const sampleTissueTypes = Array.from(sampleGuids).map(sampleGuid => ([
      sampleGuid, TISSUE_DISPLAY[(samplesByGuid || {})[sampleGuid]?.tissueType] || 'No Tissue',
    ]))

    return sampleTissueTypes.map(([sampleGuid, tissueType]) => ({
      key: tissueType, text: tissueType, value: sampleGuid,
    }))
  }

  onTissueChange = (sampleGuid) => {
    this.setState({ sampleGuid })
  }

  render() {
    const { individual, rnaSeqData, significantJunctionOutliers, genesById } = this.props
    const { sampleGuid, tissueOptions } = this.state

    const outlierData = Object.entries(rnaSeqData || {}).map(([key, data]) => [
      key,
      OUTLIER_VOLCANO_PLOT_CONFIGS[key].formatData({ data: Object.values(data || {}).flat(), sampleGuid }),
    ]).filter(([, data]) => data.length)

    const outlierPlots = outlierData.map(([key, data]) => (
      <Grid.Column key={key}>
        <RnaSeqOutliers
          familyGuid={individual.familyGuid}
          rnaSeqData={data}
          genesById={genesById}
          {...OUTLIER_VOLCANO_PLOT_CONFIGS[key]}
        />
      </Grid.Column>
    ))
    const hasSpliceOutliers = outlierData.map(([key]) => key).includes('spliceOutliers')

    return (
      <Grid>
        <React.Suspense fallback={<Loader />}>
          {hasSpliceOutliers && (
            <Grid.Row>
              <span>
                Select a tissue type: &nbsp;
                <Dropdown inline value={sampleGuid} options={tissueOptions} onChange={this.onTissueChange} />
              </span>
            </Grid.Row>
          )}
          {outlierPlots.length > 0 && <Grid.Row divided columns={outlierPlots.length}>{outlierPlots}</Grid.Row>}
        </React.Suspense>
        {significantJunctionOutliers.length && (
          <Grid.Row centered columns={14}>
            <React.Suspense fallback={<Loader />}>
              <RnaSeqOutliersTable
                familyGuid={individual.familyGuid}
                data={significantJunctionOutliers}
              />
            </React.Suspense>
          </Grid.Row>
        )}
      </Grid>
    )
  }

}

const RnaSeqResultPage = React.memo(({ individual, rnaSeqData, load, loading, ...props }) => (
  <DataLoader content={rnaSeqData} contentId={individual.individualGuid} load={load} loading={loading}>
    <BaseRnaSeqResultPage individual={individual} rnaSeqData={rnaSeqData} {...props} />
  </DataLoader>
))

RnaSeqResultPage.propTypes = {
  individual: PropTypes.object,
  rnaSeqData: PropTypes.object,
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

export default connect(mapStateToProps, mapDispatchToProps)(RnaSeqResultPage)
