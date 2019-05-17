import React from 'react'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import PropTypes from 'prop-types'
import { Header, Table } from 'semantic-ui-react'

import DataLoader from 'shared/components/DataLoader'
import { SubmissionGeneVariants, Phenotypes } from 'shared/components/panel/MatchmakerPanel'
import SortableTable from 'shared/components/table/SortableTable'
import {
  getMmeMetricsLoading,
  getMmeMetricsLoadingError,
  getMmeMetrics,
  getMmeSubmissionsLoading,
  getMmeSubmissions,
} from '../selectors'
import { loadMmeMetrics, loadMmeSubmissions } from '../reducers'

const METRICS_FIELDS = [
  { field: 'numberOfCases', title: 'Patients' },
  { field: 'numberOfUniqueGenes', title: 'Genes' },
  { field: 'numberOfUniqueFeatures', title: 'Phenotypes' },
  { field: 'numberOfCasesWithDiagnosis', title: 'Patients with Diagnosis' },
  { field: 'meanNumberOfGenesPerCase', title: 'Mean Number of Genes Per Patient', round: true },
  { field: 'meanNumberOfPhenotypesPerCase', title: 'Mean Number of Phenotypes Per Patient', round: true },
  { field: 'meanNumberOfVariantsPerCase', title: 'Mean Number of Detailed Variants Per Patient', round: true },
  { field: 'numberOfRequestsReceived', title: 'Match Requests Received' },
  { field: 'numberOfPotentialMatchesSent', title: 'Potential Matches Sent' },
  { field: 'percentageOfGenesThatMatch', title: 'Percentage of Genes Contributing to Matches', round: true },
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
  { name: 'mmeSubmittedDate', content: 'Submitted Date', format: row => new Date(row.mmeSubmittedDate).toLocaleDateString() },
  {
    name: 'mmeSubmittedData.geneVariants',
    content: 'Genes',
    format: row =>
      <SubmissionGeneVariants geneVariants={row.mmeSubmittedData.geneVariants} modalId={row.individualGuid} />,
  },
  { name: 'mmeSubmittedData.phenotypes',
    content: 'Phenotypes',
    format: row => <Phenotypes phenotypes={row.mmeSubmittedData.phenotypes} maxWidth="400px" />,
  },
  { name: 'mmeSubmittedData.patient.label', content: 'MME Patient Label', format: row => row.mmeSubmittedData.patient.label },
]

const getRowFilterVal = row => row.geneSymbols + row.mmeSubmittedData.patient.label

const Matchmaker = ({ metrics, submissions, error, metricsLoading, loadMetrics, submissionsLoading, loadSubmissions }) =>
  <div>
    <Header size="medium" content="Matchmaker Metrics:" />
    <DataLoader load={loadMetrics} content={Object.keys(metrics).length} loading={metricsLoading} errorMessage={error}>
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
    <DataLoader load={loadSubmissions} loading={false} content>
      <SortableTable
        collapsing
        idField="individualGuid"
        defaultSortColumn="mmeSubmittedDate"
        defaultSortDescending
        getRowFilterVal={getRowFilterVal}
        emptyContent="No MME Submissions Found"
        loading={submissionsLoading}
        data={submissions}
        columns={SUBMISSION_COLUMNS}
      />
    </DataLoader>
  </div>

Matchmaker.propTypes = {
  metrics: PropTypes.object,
  metricsLoading: PropTypes.bool,
  error: PropTypes.string,
  loadMetrics: PropTypes.func,
  submissions: PropTypes.array,
  submissionsLoading: PropTypes.bool,
  loadSubmissions: PropTypes.func,
}

const mapStateToProps = state => ({
  metrics: getMmeMetrics(state),
  metricsLoading: getMmeMetricsLoading(state),
  error: getMmeMetricsLoadingError(state),
  submissions: getMmeSubmissions(state),
  submissionsLoading: getMmeSubmissionsLoading(state),
})

const mapDispatchToProps = {
  loadMetrics: loadMmeMetrics,
  loadSubmissions: loadMmeSubmissions,
}

export default connect(mapStateToProps, mapDispatchToProps)(Matchmaker)
