import React from 'react'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Form } from 'semantic-ui-react'
import PropTypes from 'prop-types'
import { Header, Table } from 'semantic-ui-react'

import StateDataLoader from 'shared/components/StateDataLoader'
import { StyledForm } from 'shared/components/form/FormHelpers'
import AwesomeBar from 'shared/components/page/AwesomeBar'
import { SubmissionGeneVariants, Phenotypes } from 'shared/components/panel/MatchmakerPanel'
import DataTable from 'shared/components/table/DataTable'

const SEARCH_CATEGORIES = ['hpo_terms']

const SUBMISSION_COLUMNS = [
  {
    name: 'individualId',
    content: 'Submitted Individual',
    format: row => (
      <Link to={`/project/${row.projectGuid}/family_page/${row.familyGuid}/matchmaker_exchange`} target="_blank">
        {row.individualId}
      </Link>
    ),
  },
  { name: 'lastModifiedDate', content: 'Submitted Date', format: row => new Date(row.lastModifiedDate).toLocaleDateString() },
  {
    name: 'geneVariants',
    content: 'Genes',
    format: row => <SubmissionGeneVariants geneVariants={row.geneVariants} modalId={row.submissionGuid} />,
  },
  {
    name: 'phenotypes',
    content: 'Phenotypes',
    format: row => <Phenotypes phenotypes={row.phenotypes} maxWidth="400px" />,
  },
  { name: 'label', content: 'MME Patient Label', format: row => row.label },
]

const getRowFilterVal = row => row.geneSymbols + row.label

const getHref = history => result => {
  console.log(history, result)
  return '/summary_data/hpo_terms'
}

const parseResponse = responseJson => responseJson

const Hpo = React.memo(({ match, history }) => (
  <div>
    <StyledForm>
      <Form.Field
        control={AwesomeBar}
        categories={SEARCH_CATEGORIES}
        inputwidth="300px"
        label="HPO Term"
        placeholder="Search for an HPO term"
        getResultHref={getHref(match)}
        inline
      />
    </StyledForm>
    {match.params.hpoTerms ? (
      <StateDataLoader
        contentId={match.params.hpoTerms}
        url="/api/summary_data/hpo"
        childComponent={DataTable}
        parseResponse={parseResponse}
        collapsing
        reloadOnIdUpdate
        idField="submissionGuid"
        defaultSortColumn="lastModifiedDate"
        defaultSortDescending
        getRowFilterVal={getRowFilterVal}
        emptyContent="No MME Submissions Found"
        columns={SUBMISSION_COLUMNS}
      />
    ) : null}
  </div>
))

Hpo.propTypes = {
  history: PropTypes.object,
  match: PropTypes.object,
}

export default Hpo
