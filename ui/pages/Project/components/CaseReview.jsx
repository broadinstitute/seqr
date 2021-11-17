import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import {
  FAMILY_FIELD_DESCRIPTION,
  FAMILY_FIELD_ANALYSIS_NOTES,
  FAMILY_FIELD_CASE_NOTES,
  FAMILY_FIELD_INTERNAL_NOTES,
  FAMILY_FIELD_INTERNAL_SUMMARY,
  FAMILY_FIELD_CODED_PHENOTYPE,
  FAMILY_FIELD_ASSIGNED_ANALYST,
} from 'shared/utils/constants'
import { CASE_REVIEW_TABLE_NAME } from '../constants'
import { getCaseReviewStatusCounts } from '../selectors'
import FamilyTable from './FamilyTable/FamilyTable'

const FIELDS = [
  { id: FAMILY_FIELD_DESCRIPTION },
  { id: FAMILY_FIELD_ASSIGNED_ANALYST },
  { id: FAMILY_FIELD_CASE_NOTES },
  { id: FAMILY_FIELD_ANALYSIS_NOTES },
  { id: FAMILY_FIELD_CODED_PHENOTYPE },
  { id: FAMILY_FIELD_INTERNAL_NOTES },
  { id: FAMILY_FIELD_INTERNAL_SUMMARY },
]

const CaseReviewTable = React.memo((props) => {
  const headerStatus = { title: 'Individual Statuses', data: props.caseReviewStatusCounts }
  return (
    <div>
      <FamilyTable
        showDetails
        tableName={CASE_REVIEW_TABLE_NAME}
        headerStatus={headerStatus}
        detailFields={FIELDS}
      />
    </div>
  )
})


export { CaseReviewTable as CaseReviewTableComponent }

CaseReviewTable.propTypes = {
  caseReviewStatusCounts: PropTypes.array,
}

const mapStateToProps = state => ({
  caseReviewStatusCounts: getCaseReviewStatusCounts(state),
})

export default connect(mapStateToProps)(CaseReviewTable)
