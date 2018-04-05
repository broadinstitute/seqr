import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { Table, Form } from 'semantic-ui-react'

import { getProject } from 'redux/rootReducer'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'

import TableBody from './components/table-body/TableBody'

const CaseReviewTable = props =>
  <Form>
    <div style={{ float: 'right', padding: '0px 65px 10px 0px' }}>
      <ExportTableButton urls={[
        { name: 'Families', url: `/api/project/${props.project.projectGuid}/export_case_review_families` },
        { name: 'Individuals', url: `/api/project/${props.project.projectGuid}/export_case_review_individuals` }]}
      />
    </div>
    <Table celled style={{ width: '100%' }}>
      <TableBody />
    </Table>
  </Form>

export { CaseReviewTable as CaseReviewTableComponent }

CaseReviewTable.propTypes = {
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(CaseReviewTable)
