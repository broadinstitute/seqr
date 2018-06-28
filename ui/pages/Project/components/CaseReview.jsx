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
import { getProject, getCaseReviewStatusCounts } from '../selectors'
import FamilyTable from './FamilyTable/FamilyTable'

const FIELDS = [
  { id: FAMILY_FIELD_DESCRIPTION },
  { id: FAMILY_FIELD_ANALYSED_BY },
  { id: FAMILY_FIELD_ANALYSIS_NOTES },
  { id: FAMILY_FIELD_ANALYSIS_SUMMARY },
  { id: FAMILY_FIELD_INTERNAL_NOTES, canEdit: true },
  { id: FAMILY_FIELD_INTERNAL_SUMMARY, canEdit: true },
]

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
        showDetails
        tableName="caseReview"
        headerStatus={headerStatus}
        exportUrls={exportUrls}
        detailFields={FIELDS}
      />
    </div>
  )
}


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
