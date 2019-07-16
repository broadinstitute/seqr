import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Header, Table } from 'semantic-ui-react'

import DataLoader from 'shared/components/DataLoader'
import { getSeqrStatsLoading, getSeqrStatsLoadingError, getSeqrStats } from '../selectors'
import { loadSeqrStats } from '../reducers'

const SeqrStats = ({ stats, error, loading, load }) =>
  <div>
    <Header size="medium" content="Seqr Stats:" subheader="NOTE: counts are based on the total number of unique family/individual/sample ids" />
    <DataLoader load={load} content={Object.keys(stats).length} loading={loading} errorMessage={error}>
      <Table collapsing basic="very">
        <Table.Row>
          <Table.Cell textAlign="right"><b>Families</b></Table.Cell>
          <Table.Cell>{stats.familyCount}</Table.Cell>
        </Table.Row>
        <Table.Row>
          <Table.Cell textAlign="right"><b>Individuals</b></Table.Cell>
          <Table.Cell>{stats.individualCount}</Table.Cell>
        </Table.Row>
        {Object.entries(stats.sampleCountByType || {}).map(([sampleType, count]) =>
          <Table.Row key={sampleType}>
            <Table.Cell textAlign="right"><b>{sampleType} samples</b></Table.Cell>
            <Table.Cell>{count}</Table.Cell>
          </Table.Row>,
        )}
      </Table>
    </DataLoader>
  </div>

SeqrStats.propTypes = {
  stats: PropTypes.object,
  loading: PropTypes.bool,
  error: PropTypes.string,
  load: PropTypes.func,
}

const mapStateToProps = state => ({
  stats: getSeqrStats(state),
  loading: getSeqrStatsLoading(state),
  error: getSeqrStatsLoadingError(state),
})

const mapDispatchToProps = {
  load: loadSeqrStats,
}

export default connect(mapStateToProps, mapDispatchToProps)(SeqrStats)
