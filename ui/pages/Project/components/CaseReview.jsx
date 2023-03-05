import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import {
  FAMILY_MAIN_FIELDS,
  FAMILY_FIELD_ANALYSIS_NOTES,
  FAMILY_FIELD_CASE_NOTES,
  FAMILY_FIELD_INTERNAL_NOTES,
  FAMILY_FIELD_INTERNAL_SUMMARY,
  FAMILY_FIELD_CODED_PHENOTYPE,
} from 'shared/utils/constants'
import { CASE_REVIEW_TABLE_NAME } from '../constants'
import { getCaseReviewStatusCounts } from '../selectors'
import FamilyTable from './FamilyTable/FamilyTable'

const FIELDS = [
  ...FAMILY_MAIN_FIELDS,
  { id: FAMILY_FIELD_CASE_NOTES },
  { id: FAMILY_FIELD_ANALYSIS_NOTES },
  { id: FAMILY_FIELD_CODED_PHENOTYPE },
  { id: FAMILY_FIELD_INTERNAL_NOTES },
  { id: FAMILY_FIELD_INTERNAL_SUMMARY },
]

const CaseReviewTable = React.memo(({ headerStatus }) => (
  <div>
    <FamilyTable
      tableName={CASE_REVIEW_TABLE_NAME}
      headerStatus={headerStatus}
      detailFields={FIELDS}
    />
  </div>
))

CaseReviewTable.propTypes = {
  headerStatus: PropTypes.object,
}

const mapStateToProps = state => ({
  headerStatus: { title: 'Individual Statuses', data: getCaseReviewStatusCounts(state) },
})

export default connect(mapStateToProps)(CaseReviewTable)
