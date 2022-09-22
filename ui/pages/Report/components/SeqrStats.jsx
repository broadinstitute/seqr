import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Header, Table } from 'semantic-ui-react'

import { getUser } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import { DATASET_TITLE_LOOKUP } from 'shared/utils/constants'
import { getSeqrStatsLoading, getSeqrStatsLoadingError, getSeqrStats } from '../selectors'
import { loadSeqrStats } from '../reducers'

const DEMO_COLUMN = { title: 'Demo Projects', key: 'demo' }
const COLUMN_MAP = {
  [true]: [
    { title: 'Internal Projects', key: 'internal' },
    { title: 'External AnVIL Projects', key: 'external' },
    DEMO_COLUMN,
    { title: 'No AnVIL Projects', key: 'no_anvil' },
  ],
  [false]: [
    { title: 'Data Projects', key: 'non_demo' },
    DEMO_COLUMN,
  ],
}

const SeqrStats = React.memo(({ stats, error, loading, load, user }) => (
  <div>
    <Header size="large" content="Seqr Stats:" />
    <DataLoader load={load} content={Object.keys(stats).length} loading={loading} errorMessage={error}>
      <Table collapsing basic="very" textAlign="right">
        <Table.Header>
          <Table.Row>
            <Table.HeaderCell />
            {COLUMN_MAP[user.isAnvil].map(({ title }) => <Table.HeaderCell key={title} content={title} />)}
          </Table.Row>
        </Table.Header>
        {['Projects', 'Families', 'Individuals'].map(field => (
          <Table.Row key={field}>
            <Table.HeaderCell textAlign="right" content={field} />
            {COLUMN_MAP[user.isAnvil].map(({ key }) => (
              <Table.Cell key={key} content={(stats[`${field.toLowerCase()}Count`] || {})[key]} />
            ))}
          </Table.Row>
        ))}
        {Object.keys(stats.sampleCountsByType || {}).sort().map(sampleTypes => (
          <Table.Row key={sampleTypes}>
            <Table.HeaderCell
              textAlign="right"
              content={`${sampleTypes.split('__')[0]}${DATASET_TITLE_LOOKUP[sampleTypes.split('__')[1]] || ''} samples`}
            />
            {COLUMN_MAP[user.isAnvil].map(({ key }) => (
              <Table.Cell key={key} content={stats.sampleCountsByType[sampleTypes][key]} />
            ))}
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
  user: PropTypes.object,
}

const mapStateToProps = state => ({
  user: getUser(state),
  stats: getSeqrStats(state),
  loading: getSeqrStatsLoading(state),
  error: getSeqrStatsLoadingError(state),
})

const mapDispatchToProps = {
  load: loadSeqrStats,
}

export default connect(mapStateToProps, mapDispatchToProps)(SeqrStats)
