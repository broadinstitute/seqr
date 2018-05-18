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

const DETAIL_FIELDS = [
  { id: FAMILY_FIELD_DESCRIPTION },
  { id: FAMILY_FIELD_ANALYSED_BY },
  { id: FAMILY_FIELD_ANALYSIS_NOTES },
  { id: FAMILY_FIELD_ANALYSIS_SUMMARY },
]

const NO_DETAIL_FIELDS = [
  { id: FAMILY_FIELD_INTERNAL_NOTES, canEdit: true },
  { id: FAMILY_FIELD_INTERNAL_SUMMARY, canEdit: true },
]

const ALL_FIELDS = DETAIL_FIELDS.concat(NO_DETAIL_FIELDS)

const CaseReviewTable = (props) => {
  const headerStatus = { title: 'Individual Statuses', data: props.caseReviewStatusCounts }
  const exportUrls = [
    { name: 'Families', url: `/api/project/${props.project.projectGuid}/export_case_review_families` },
    { name: 'Individuals', url: `/api/project/${props.project.projectGuid}/export_case_review_individuals` },
  ]
  return (
    <div>
      <FamilyTable
        showInternalFilters
        editCaseReview
        headerStatus={headerStatus}
        exportUrls={exportUrls}
        fields={props.showDetails ? ALL_FIELDS : NO_DETAIL_FIELDS}
      />
    </div>
  )
}


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
