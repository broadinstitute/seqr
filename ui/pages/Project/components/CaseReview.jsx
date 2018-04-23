import React from 'react'
import PropTypes from 'prop-types'
import DocumentTitle from 'react-document-title'
import { connect } from 'react-redux'

import { getProject } from 'redux/rootReducer'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'

import FamilyTable from './FamilyTable/FamilyTable'

const CaseReviewTable = props =>
  <div>
    <DocumentTitle title={`Case Review: ${props.project.name}`} />
    <div style={{ float: 'right', padding: '0px 65px 10px 0px' }}>
      <ExportTableButton urls={[
        { name: 'Families', url: `/api/project/${props.project.projectGuid}/export_case_review_families` },
        { name: 'Individuals', url: `/api/project/${props.project.projectGuid}/export_case_review_individuals` }]}
      />
    </div>
    <FamilyTable showHeaderStatusBar showInternalFields editCaseReview />
  </div>

export { CaseReviewTable as CaseReviewTableComponent }

CaseReviewTable.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(CaseReviewTable)
