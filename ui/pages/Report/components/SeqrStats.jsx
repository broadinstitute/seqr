import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Header, Table } from 'semantic-ui-react'

import DataLoader from 'shared/components/DataLoader'
import { DATASET_TITLE_LOOKUP } from 'shared/utils/constants'
import { getSeqrStatsLoading, getSeqrStatsLoadingError, getSeqrStats } from '../selectors'
import { loadSeqrStats } from '../reducers'

const SeqrStats = React.memo(({ stats, error, loading, load }) => (
  <div>
    <Header size="large" content="Seqr Stats:" />
    <DataLoader load={load} content={Object.keys(stats).length} loading={loading} errorMessage={error}>
      <Table collapsing basic="very">
        <Table.Header>
          <Table.Row>
            <Table.HeaderCell />
            <Table.HeaderCell content="Internal Projects" />
            <Table.HeaderCell content="External AnVIL Projects" />
          </Table.Row>
        </Table.Header>
        {['Projects', 'Families', 'Individuals'].map(field => (
          <Table.Row key={field}>
            <Table.HeaderCell textAlign="right" content={field} />
            <Table.Cell content={stats[`${field.toLowerCase()}Count`]?.internal} />
            <Table.Cell content={stats[`${field.toLowerCase()}Count`]?.external} />
          </Table.Row>
        ))}
        {Object.keys(stats.sampleCountsByType || {}).sort().map(sampleTypes => (
          <Table.Row key={sampleTypes}>
            <Table.HeaderCell
              textAlign="right"
              content={`${sampleTypes.split('__')[0]}${DATASET_TITLE_LOOKUP[sampleTypes.split('__')[1]] || ''} samples`}
            />
            <Table.Cell content={stats.sampleCountsByType[sampleTypes].internal} />
            <Table.Cell content={stats.sampleCountsByType[sampleTypes].external} />
          </Table.Row>
        ))}
      </Table>
    </DataLoader>
  </div>
))

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
