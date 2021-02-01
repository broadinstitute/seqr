import React from 'react'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import PropTypes from 'prop-types'
import { Header, Table } from 'semantic-ui-react'

import { getUser } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import { SubmissionGeneVariants, Phenotypes } from 'shared/components/panel/MatchmakerPanel'
import DataTable from 'shared/components/table/DataTable'
import {
  getMmeLoading,
  getMmeLoadingError,
  getMmeMetrics,
  getMmeSubmissions,
} from '../selectors'
import { loadMme } from '../reducers'

const METRICS_FIELDS = [
  { field: 'numberOfCases', title: 'Patients' },
  { field: 'numberOfUniqueGenes', title: 'Genes' },
  { field: 'numberOfUniqueFeatures', title: 'Phenotypes' },
  { field: 'numberOfRequestsReceived', title: 'Match Requests Received' },
  { field: 'numberOfPotentialMatchesSent', title: 'Potential Matches Sent' },
  { field: 'numberOfSubmitters', title: 'Submitters' },
]

const SUBMISSION_COLUMNS = [
  {
    name: 'individualId',
    content: 'Submitted Individual',
    format: row =>
      <Link to={`/project/${row.projectGuid}/family_page/${row.familyGuid}/matchmaker_exchange`} target="_blank">
        {row.individualId}
      </Link>,
  },
  { name: 'lastModifiedDate', content: 'Submitted Date', format: row => new Date(row.lastModifiedDate).toLocaleDateString() },
  {
    name: 'geneVariants',
    content: 'Genes',
    format: row =>
      <SubmissionGeneVariants geneVariants={row.geneVariants} modalId={row.submissionGuid} />,
  },
  { name: 'phenotypes',
    content: 'Phenotypes',
    format: row => <Phenotypes phenotypes={row.phenotypes} maxWidth="400px" />,
  },
  { name: 'label', content: 'MME Patient Label', format: row => row.label },
]

const getRowFilterVal = row => row.geneSymbols + row.label

const Matchmaker = React.memo(({ metrics, submissions, error, loading, load, user }) =>
  <div>
    {user.isAnalyst && <Header size="medium" content="Matchmaker Metrics:" /> }
    <DataLoader load={load} content={Object.keys(metrics).length} loading={loading} errorMessage={error} hideError={!user.isAnalyst}>
      <Table collapsing basic="very">
        {METRICS_FIELDS.map(({ field, title, round }) =>
          <Table.Row key={field}>
            <Table.Cell textAlign="right"><b>{title}</b></Table.Cell>
            <Table.Cell>{round && metrics[field] ? metrics[field].toPrecision(3) : metrics[field]}</Table.Cell>
          </Table.Row>,
        )}
      </Table>
    </DataLoader>
    <Header size="medium" content="Matchmaker Submissions:" />
    <DataTable
      collapsing
      idField="submissionGuid"
      defaultSortColumn="lastModifiedDate"
      defaultSortDescending
      getRowFilterVal={getRowFilterVal}
      emptyContent="No MME Submissions Found"
      loading={loading}
      data={submissions}
      columns={SUBMISSION_COLUMNS}
    />
  </div>,
)

Matchmaker.propTypes = {
  metrics: PropTypes.object,
  loading: PropTypes.bool,
  error: PropTypes.string,
  load: PropTypes.func,
  submissions: PropTypes.array,
  user: PropTypes.object,
}

const mapStateToProps = state => ({
  metrics: getMmeMetrics(state),
  loading: getMmeLoading(state),
  error: getMmeLoadingError(state),
  submissions: getMmeSubmissions(state),
  user: getUser(state),
})

const mapDispatchToProps = {
  load: loadMme,
}

export default connect(mapStateToProps, mapDispatchToProps)(Matchmaker)
