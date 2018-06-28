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
import { getCaseReviewStatusCounts, getFamiliesExportConfig, getIndividualsExportConfig } from '../selectors'
import FamilyTable from './FamilyTable/FamilyTable'

const FIELDS = [
  { id: FAMILY_FIELD_DESCRIPTION },
  { id: FAMILY_FIELD_ANALYSED_BY },
  { id: FAMILY_FIELD_ANALYSIS_NOTES },
  { id: FAMILY_FIELD_ANALYSIS_SUMMARY },
  { id: FAMILY_FIELD_INTERNAL_NOTES, canEdit: true },
  { id: FAMILY_FIELD_INTERNAL_SUMMARY, canEdit: true },
]

const tableName = 'Case Review'

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
        tableName={tableName}
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
  familyExportConfig: getFamiliesExportConfig(state, { tableName, internal: true }),
  individualsExportConfig: getIndividualsExportConfig(state, { tableName, internal: true }),
})

export default connect(mapStateToProps)(CaseReviewTable)
