import React from 'react'
import { connect } from 'react-redux'
import { Table, Form } from 'semantic-ui-react'

import TableBody from './table-body/TableBody'
import ExportTableButton from '../../../shared/components/ExportTableButton'
import { getProject } from '../reducers/rootReducer'

const CaseReviewTable = props => <Form>
  <div style={{ float: 'right', padding: '0px 65px 10px 0px' }}>
    <ExportTableButton urls={[
      { name: 'Families Table', url: `/api/project/${props.project.projectGuid}/export_case_review_families` },
      { name: 'Individuals Table', url: `/api/project/${props.project.projectGuid}/export_case_review_individuals` }]}
    />
  </div>
  <Table celled style={{ width: '100%' }}>
    <TableBody />
  </Table>
</Form>

export { CaseReviewTable as CaseReviewTableComponent }

CaseReviewTable.propTypes = {
  project: React.PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(CaseReviewTable)
