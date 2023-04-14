import React from 'react'
import PropTypes from 'prop-types'
import { Grid } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { getGenesById, getRnaSeqSpliceDataByIndividual } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import { GeneSearchLink } from 'shared/components/buttons/SearchResultsLink'
import DataTable from 'shared/components/table/DataTable'
import { camelcaseToTitlecase } from 'shared/utils/stringUtils'
import { loadRnaSeqSpliceData } from '../reducers'
import { getRnaSeqSpliceDataLoading } from '../selectors'
import RnaSeqOutlierVolcanoPlot from './RnaSeqOutlierVolcanoPlot'

const RNA_SEQ_SPLICE_NUM_FIELDS = ['zScore', 'pValue', 'deltaPsi']
const RNA_SEQ_SPLICE_DETAIL_FIELDS = ['geneId', 'chrom', 'start', 'end', 'strand', 'zScore', 'pValue', 'type', 'deltaPsi',
  'readCount', 'rareDiseaseSamplesWithJunction', 'rareDiseaseSamplesTotal']

const RNA_SEQ_SPLICE_COLUMNS = [
  ...RNA_SEQ_SPLICE_DETAIL_FIELDS.map(name => (
    {
      name,
      content: camelcaseToTitlecase(name).replace(' ', '-'),
      format: row => (RNA_SEQ_SPLICE_NUM_FIELDS.includes(name) ? row[name].toPrecision(3) : row[name]),
    }
  )),
]

const RnaSeqSpliceDataTable = React.memo(({ data, loading }) => (
  <DataTable
    data={Object.values(data)}
    loading={loading}
    idField="geneId"
    columns={RNA_SEQ_SPLICE_COLUMNS}
  />
))

RnaSeqSpliceDataTable.propTypes = {
  data: PropTypes.object,
  loading: PropTypes.bool,
}

const BaseRnaSeqSpliceOutliers = React.memo((
  { individualGuid, rnaSeqSpliceData, genesById, familyGuid, loading, load },
) => (
  <DataLoader content={rnaSeqSpliceData} contentId={individualGuid} load={load} loading={loading}>
    <Grid.Row width={6}>
      <GeneSearchLink
        buttonText="Search for variants in splice outlier genes"
        icon="search"
        location={Object.values(rnaSeqSpliceData || {}).filter(({ isSignificant }) => isSignificant).map(({ geneId }) => geneId).join(',')}
        familyGuid={familyGuid}
        floated="right"
      />
      <RnaSeqOutlierVolcanoPlot data={rnaSeqSpliceData} genesById={genesById} />
    </Grid.Row>
    <Grid.Row>
      <RnaSeqSpliceDataTable
        data={rnaSeqSpliceData}
        loading={loading}
      />
    </Grid.Row>
  </DataLoader>
))

BaseRnaSeqSpliceOutliers.propTypes = {
  individualGuid: PropTypes.string.isRequired,
  familyGuid: PropTypes.string.isRequired,
  rnaSeqSpliceData: PropTypes.object,
  genesById: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  rnaSeqSpliceData: getRnaSeqSpliceDataByIndividual(state)[ownProps.individualGuid]?.spliceOutliers,
  genesById: getGenesById(state),
  loading: getRnaSeqSpliceDataLoading(state),
})

const mapDispatchToProps = {
  load: loadRnaSeqSpliceData,
}

export default connect(mapStateToProps, mapDispatchToProps)(BaseRnaSeqSpliceOutliers)
