import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Loader, Grid, Dropdown } from 'semantic-ui-react'

import { getGenesById, getIndividualsByGuid, getRnaSeqDataByIndividual, getRnaSeqSignificantJunctionData } from 'redux/selectors'
import { RNASEQ_JUNCTION_PADDING } from 'shared/utils/constants'
import DataLoader from 'shared/components/DataLoader'
import FamilyReads from 'shared/components/panel/family/FamilyReads'
import RnaSeqJunctionOutliersTable from 'shared/components/table/RnaSeqJunctionOutliersTable'
import { loadRnaSeqData } from '../reducers'
import { getRnaSeqDataLoading, getTissueOptionsByIndividualGuid } from '../selectors'

const RnaSeqOutliers = React.lazy(() => import('./RnaSeqOutliers'))

const OUTLIER_VOLCANO_PLOT_CONFIGS = [
  {
    key: 'outliers',
    getLocation: (({ geneId }) => geneId),
    searchType: 'genes',
    title: 'Expression Outliers',
    formatData: data => data,
  },
  {
    key: 'spliceOutliers',
    getLocation: (({ chrom, start, end }) => `${chrom}:${Math.max(1, start - RNASEQ_JUNCTION_PADDING)}-${end + RNASEQ_JUNCTION_PADDING}`),
    searchType: 'regions',
    title: 'Splice Junction Outliers',
    formatData: (data, tissueType) => data.filter(outlier => outlier.tissueType === tissueType),
  },
]

class BaseRnaSeqResultPage extends React.PureComponent {

  static propTypes = {
    familyGuid: PropTypes.string,
    rnaSeqData: PropTypes.object,
    significantJunctionOutliers: PropTypes.arrayOf(PropTypes.object),
    genesById: PropTypes.object,
    tissueOptions: PropTypes.arrayOf(PropTypes.object),
  }

  constructor(props) {
    super(props)
    const { tissueOptions } = props

    // eslint-disable-next-line react/state-in-constructor
    this.state = {
      tissueType: tissueOptions.length > 0 ? tissueOptions[0].value : null,
      tissueOptions,
    }
  }

  onTissueChange = (tissueType) => {
    this.setState({ tissueType })
  }

  render() {
    const { familyGuid, rnaSeqData, significantJunctionOutliers, genesById } = this.props
    const { tissueType, tissueOptions } = this.state

    const outlierPlotConfigs = OUTLIER_VOLCANO_PLOT_CONFIGS.map(({ formatData, ...config }) => ({
      data: formatData(Object.values((rnaSeqData || {})[config.key] || {}).flat(), tissueType),
      ...config,
    })).filter(({ data }) => data.length)

    const outlierPlots = outlierPlotConfigs.map(({ key, data, ...config }) => (
      <Grid.Column key={key} width={8}>
        <RnaSeqOutliers
          familyGuid={familyGuid}
          rnaSeqData={data}
          genesById={genesById}
          {...config}
        />
      </Grid.Column>
    ))

    return (
      <div>
        {tissueType && (
          <span>
            Tissue type: &nbsp;
            {tissueOptions.length > 1 ? (
              <Dropdown inline value={tissueType} options={tissueOptions} onChange={this.onTissueChange} />
            ) : tissueOptions[0].text }
          </span>
        )}
        <React.Suspense fallback={<Loader />}>
          {(outlierPlots.length > 0) && (
            <Grid>
              <Grid.Row divided columns={outlierPlots.length}>{outlierPlots}</Grid.Row>
            </Grid>
          )}
        </React.Suspense>
        {(significantJunctionOutliers.length > 0) && (
          <FamilyReads
            layout={RnaSeqJunctionOutliersTable}
            noTriggerButton
            data={significantJunctionOutliers}
            defaultSortColumn="pValue"
            maxHeight="600px"
          />
        )}
      </div>
    )
  }

}

const RnaSeqResultPage = React.memo(({ individual, rnaSeqData, load, loading, ...props }) => (
  <DataLoader content={rnaSeqData} contentId={individual.individualGuid} load={load} loading={loading}>
    <BaseRnaSeqResultPage familyGuid={individual.familyGuid} rnaSeqData={rnaSeqData} {...props} />
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
  tissueOptions: getTissueOptionsByIndividualGuid(state)[ownProps.match.params.individualGuid],
  loading: getRnaSeqDataLoading(state),
})

const mapDispatchToProps = {
  load: loadRnaSeqData,
}

export default connect(mapStateToProps, mapDispatchToProps)(RnaSeqResultPage)
