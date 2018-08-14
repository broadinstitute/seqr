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
  FAMILY_FIELD_CODED_PHENOTYPE,
} from 'shared/utils/constants'
import { CASE_REVIEW_TABLE_NAME } from '../constants'
import { getCaseReviewStatusCounts, getFamiliesExportConfig, getIndividualsExportConfig } from '../selectors'
import FamilyTable from './FamilyTable/FamilyTable'

const FIELDS = [
  { id: FAMILY_FIELD_DESCRIPTION, canEdit: true },
  { id: FAMILY_FIELD_ANALYSED_BY },
  { id: FAMILY_FIELD_ANALYSIS_NOTES, canEdit: true },
  { id: FAMILY_FIELD_ANALYSIS_SUMMARY },
  { id: FAMILY_FIELD_CODED_PHENOTYPE, canEdit: true },
  { id: FAMILY_FIELD_INTERNAL_NOTES, canEdit: true },
  { id: FAMILY_FIELD_INTERNAL_SUMMARY, canEdit: true },
]

const CaseReviewTable = (props) => {
  const headerStatus = { title: 'Individual Statuses', data: props.caseReviewStatusCounts }
  const exportUrls = [
    { name: 'Families', data: props.familyExportConfig },
    { name: 'Individuals', data: props.individualsExportConfig },
  ]
  return (
    <div>
      <FamilyTable
        showInternalFilters
        editCaseReview
        showDetails
        tableName={CASE_REVIEW_TABLE_NAME}
        headerStatus={headerStatus}
        exportUrls={exportUrls}
        detailFields={FIELDS}
      />
    </div>
  )
}


export { CaseReviewTable as CaseReviewTableComponent }

CaseReviewTable.propTypes = {
  caseReviewStatusCounts: PropTypes.array,
  familyExportConfig: PropTypes.object,
  individualsExportConfig: PropTypes.object,
}

const mapStateToProps = state => ({
  caseReviewStatusCounts: getCaseReviewStatusCounts(state),
  familyExportConfig: getFamiliesExportConfig(state, { tableName: CASE_REVIEW_TABLE_NAME, internal: true }),
  individualsExportConfig: getIndividualsExportConfig(state, { tableName: CASE_REVIEW_TABLE_NAME, internal: true }),
})

export default connect(mapStateToProps)(CaseReviewTable)
