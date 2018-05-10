import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import {
  FAMILY_FIELD_DESCRIPTION,
  FAMILY_FIELD_ANALYSED_BY,
  FAMILY_FIELD_ANALYSIS_NOTES,
  FAMILY_FIELD_ANALYSIS_SUMMARY,
  FAMILY_FIELD_INTERNAL_NOTES,
  FAMILY_FIELD_INTERNAL_SUMMARY,
} from 'shared/utils/constants'
import { getShowDetails, getProject, getCaseReviewStatusCounts } from '../selectors'
import FamilyTable from './FamilyTable/FamilyTable'

const CaseReviewTable = props =>
  <FamilyTable
    showInternalFilters
    editCaseReview
    headerStatus={{ title: 'Individual Statuses', data: props.caseReviewStatusCounts }}
    exportUrls={[
      { name: 'Families', url: `/api/project/${props.project.projectGuid}/export_case_review_families` },
      { name: 'Individuals', url: `/api/project/${props.project.projectGuid}/export_case_review_individuals` },
    ]}
    fields={props.showDetails ? [
      { id: FAMILY_FIELD_DESCRIPTION },
      { id: FAMILY_FIELD_ANALYSED_BY },
      { id: FAMILY_FIELD_ANALYSIS_NOTES },
      { id: FAMILY_FIELD_ANALYSIS_SUMMARY },
      { id: FAMILY_FIELD_INTERNAL_NOTES, canEdit: true },
      { id: FAMILY_FIELD_INTERNAL_SUMMARY, canEdit: true },
    ] : [
      { id: FAMILY_FIELD_INTERNAL_NOTES, canEdit: true },
      { id: FAMILY_FIELD_INTERNAL_SUMMARY, canEdit: true },
    ]}
  />

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
