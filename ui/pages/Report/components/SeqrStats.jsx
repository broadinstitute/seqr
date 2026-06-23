import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { Header, Table, Grid } from 'semantic-ui-react'

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
const USER_ROWS = [
  { title: 'Total', key: 'total' },
  { title: 'Logged In More Than Once', key: 'multipleLogins' },
  { title: 'Logged In Within 30 Days', key: 'lastMonth' },
  { title: 'Logged In Within 365 Days', key: 'lastYear' },
  { title: 'Logged In This Year', key: 'thisYear' },
]

const SeqrStats = React.memo(({ stats, error, loading, load, user }) => (
  <div>
    <Header size="large" content="Seqr Stats:" />
    <DataLoader load={load} content={Object.keys(stats).length} loading={loading} errorMessage={error}>
      <Grid columns={2}>
        <Grid.Row>
          <Grid.Column>
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
          </Grid.Column>
          <Grid.Column>
            <Table collapsing basic="very" textAlign="right">
              <Table.Header>
                <Table.Row>
                  <Table.HeaderCell />
                  <Table.HeaderCell content="Users" />
                </Table.Row>
                {USER_ROWS.map(({ title, key }) => (
                  <Table.Row key={key}>
                    <Table.HeaderCell textAlign="right" content={title} />
                    <Table.Cell content={(stats.usersCounts || {})[key]} />
                  </Table.Row>
                ))}
              </Table.Header>
            </Table>
          </Grid.Column>
        </Grid.Row>
      </Grid>
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
