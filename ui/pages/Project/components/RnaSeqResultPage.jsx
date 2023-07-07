import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Loader, Grid, Dropdown } from 'semantic-ui-react'

import { getGenesById, getIndividualsByGuid, getRnaSeqSignificantJunctionData } from 'redux/selectors'
import { RNASEQ_JUNCTION_PADDING, TISSUE_DISPLAY } from 'shared/utils/constants'
import DataLoader from 'shared/components/DataLoader'
import FamilyReads from 'shared/components/panel/family/FamilyReads'
import RnaSeqJunctionOutliersTable from 'shared/components/table/RnaSeqJunctionOutliersTable'
import { loadRnaSeqData } from '../reducers'
import { getRnaSeqDataLoading, getRnaSeqOutliersByIndividual, getTissueOptionsByIndividualGuid } from '../selectors'

const RnaSeqOutliers = React.lazy(() => import('./RnaSeqOutliers'))

const TissueContainer = styled.div`
  margin-bottom: 1rem;
`

const OUTLIER_VOLCANO_PLOT_CONFIGS = [
  {
    key: 'outliers',
    getLocation: (({ geneId }) => geneId),
    searchType: 'genes',
    title: 'Expression Outliers',
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

  state = {
    tissueType: null,
  }

  onTissueChange = (e, data) => {
    this.setState({ tissueType: data.value })
  }

  render() {
    const { familyGuid, rnaSeqData, significantJunctionOutliers, genesById, tissueOptions } = this.props
    const { tissueType } = this.state
    const showTissueType = tissueType || (tissueOptions?.length > 0 ? tissueOptions[0].value : null)
    const tissueDisplay = TISSUE_DISPLAY[showTissueType]

    const outlierPlotConfigs = OUTLIER_VOLCANO_PLOT_CONFIGS.map(({ formatData, ...config }) => {
      const data = rnaSeqData[config.key]
      return ({ data: formatData ? formatData(data, showTissueType) : data, ...config })
    }).filter(({ data }) => data.length)

    const tableData = significantJunctionOutliers.reduce(
      (acc, outlier) => (outlier.tissueType === showTissueType ? [...acc, outlier] : acc), [],
    )

    return (
      <div>
        {showTissueType && (
          <TissueContainer>
            Tissue type: &nbsp;
            {tissueOptions.length > 1 ? (
              <Dropdown
                text={tissueDisplay || 'Unknown Tissue'}
                value={showTissueType}
                options={tissueOptions}
                onChange={this.onTissueChange}
              />
            ) : tissueDisplay}
          </TissueContainer>
        )}
        { outlierPlotConfigs.length > 0 && (
          <React.Suspense fallback={<Loader />}>
            <Grid>
              <Grid.Row divided columns={outlierPlotConfigs.length}>
                {outlierPlotConfigs.map(({ key, data, ...config }) => (
                  <Grid.Column key={key} width={8}>
                    <RnaSeqOutliers
                      familyGuid={familyGuid}
                      rnaSeqData={data}
                      genesById={genesById}
                      {...config}
                    />
                  </Grid.Column>
                ))}
              </Grid.Row>
            </Grid>
          </React.Suspense>
        )}
        {(tableData.length > 0) && (
          <FamilyReads
            layout={RnaSeqJunctionOutliersTable}
            noTriggerButton
            data={tableData}
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

const mapStateToProps = (state, { match }) => ({
  individual: getIndividualsByGuid(state)[match.params.individualGuid],
  rnaSeqData: getRnaSeqOutliersByIndividual(state)[match.params.individualGuid],
  significantJunctionOutliers: getRnaSeqSignificantJunctionData(state)[match.params.individualGuid] || [],
  genesById: getGenesById(state),
  tissueOptions: getTissueOptionsByIndividualGuid(state)[match.params.individualGuid],
  loading: getRnaSeqDataLoading(state),
})

const mapDispatchToProps = {
  load: loadRnaSeqData,
}

export default connect(mapStateToProps, mapDispatchToProps)(RnaSeqResultPage)
