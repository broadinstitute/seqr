import React from 'react'
import PropTypes from 'prop-types'
import DocumentTitle from 'react-document-title'
import { connect } from 'react-redux'

import { getProject } from 'redux/rootReducer'

import { getCaseReviewStatusCounts } from '../utils/selectors'
import FamilyTable from './FamilyTable/FamilyTable'

const CaseReviewTable = props =>
  <div>
    <DocumentTitle title={`Case Review: ${props.project.name}`} />
    <FamilyTable
      showInternalFields
      editCaseReview
      headerStatus={{ title: 'Individual Statuses', data: props.caseReviewStatusCounts }}
      exportUrls={[
        { name: 'Families', url: `/api/project/${props.project.projectGuid}/export_case_review_families` },
        { name: 'Individuals', url: `/api/project/${props.project.projectGuid}/export_case_review_individuals` },
      ]}
    />
  </div>

export { CaseReviewTable as CaseReviewTableComponent }

CaseReviewTable.propTypes = {
  project: PropTypes.object.isRequired,
  caseReviewStatusCounts: PropTypes.array,
}

const mapStateToProps = state => ({
  project: getProject(state),
  caseReviewStatusCounts: getCaseReviewStatusCounts(state),
})

export default connect(mapStateToProps)(CaseReviewTable)
