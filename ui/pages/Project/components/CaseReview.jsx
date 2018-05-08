import React from 'react'
import PropTypes from 'prop-types'
import DocumentTitle from 'react-document-title'
import { connect } from 'react-redux'

import { getProject } from 'redux/rootReducer'

import { getCaseReviewStatusCounts } from '../utils/selectors'
import { getShowDetails } from '../reducers'
import FamilyTable from './FamilyTable/FamilyTable'
import {
  DESCRIPTION, ANALYSED_BY, ANALYSIS_NOTES, ANALYSIS_SUMMARY, INTERNAL_NOTES, INTERNAL_SUMMARY,
} from './FamilyTable/FamilyRow'

const CaseReviewTable = props =>
  <div>
    <DocumentTitle title={`Case Review: ${props.project.name}`} />
    <FamilyTable
      showInternalFilters
      editCaseReview
      headerStatus={{ title: 'Individual Statuses', data: props.caseReviewStatusCounts }}
      exportUrls={[
        { name: 'Families', url: `/api/project/${props.project.projectGuid}/export_case_review_families` },
        { name: 'Individuals', url: `/api/project/${props.project.projectGuid}/export_case_review_individuals` },
      ]}
      fields={props.showDetails ? [
        { id: DESCRIPTION },
        { id: ANALYSED_BY },
        { id: ANALYSIS_NOTES },
        { id: ANALYSIS_SUMMARY },
        { id: INTERNAL_NOTES, canEdit: true },
        { id: INTERNAL_SUMMARY, canEdit: true },
      ] : [
        { id: INTERNAL_NOTES, canEdit: true },
        { id: INTERNAL_SUMMARY, canEdit: true },
      ]}
    />
  </div>

export { CaseReviewTable as CaseReviewTableComponent }

CaseReviewTable.propTypes = {
  project: PropTypes.object.isRequired,
  caseReviewStatusCounts: PropTypes.array,
  showDetails: PropTypes.bool,
}

const mapStateToProps = state => ({
  project: getProject(state),
  caseReviewStatusCounts: getCaseReviewStatusCounts(state),
  showDetails: getShowDetails(state),
})

export default connect(mapStateToProps)(CaseReviewTable)
