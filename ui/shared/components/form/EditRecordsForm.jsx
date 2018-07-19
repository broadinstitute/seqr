import React from 'react'
import PropTypes from 'prop-types'
import styled, { injectGlobal } from 'styled-components'
import { connect } from 'react-redux'
import { Table, Divider, Pagination } from 'semantic-ui-react'
import { Field, FieldArray, formValueSelector, change } from 'redux-form'
import get from 'lodash/get'

import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'

/* eslint-disable no-unused-expressions */
injectGlobal`
  
  .ui.table.basic.compact td { 
    border-top: 0px !important; 
  }
  
  .ui.table.basic.compact tr.active {
    background-color: #F3F3F3 !important;
  }
  
  .ui.table.basic.compact input[type="checkbox"] {
    cursor: pointer;
    margin: 0px 10px;
    vertical-align: middle;
  }
  
  .ui.table.basic.compact input[type="text"] {
    padding: 5px 7px;
  }

`

const DeleteButton = styled.a.attrs({ role: 'button', tabIndex: '0' })`
  cursor: pointer;
  margin: 20px 20px 5px 20px !important;
  font-size: 1.1em;
  font-weight: 500;
`

const TableHeaderCell = styled(Table.HeaderCell)`
  padding-bottom: 8px;
`

const ROWS_PER_PAGE = 12

class EditRecordsForm extends React.Component
{
  static propTypes = {
    /* Array of records to be edited in this form */
    records: PropTypes.arrayOf(PropTypes.object).isRequired,
    editedRecords: PropTypes.arrayOf(PropTypes.object),
    changeField: PropTypes.func,
    isActiveRow: PropTypes.func,

    /* Array of fields to show for a given record row */
    fields: PropTypes.arrayOf(PropTypes.object).isRequired,

    /* Unique identifier for the form */
    formName: PropTypes.string.isRequired,

    /* Unique identifier for the modal containing the form if there are multiple forms in the modal */
    modalName: PropTypes.string,

    onSubmit: PropTypes.func.isRequired,
    onClose: PropTypes.func,
  }

  constructor(props) {
    super(props)
    this.state = {
      activePage: 1,
    }
  }

  renderRow = ({ fields }) => {
    const checkboxField = {
      field: 'toDelete',
      fieldProps: { component: 'input', type: 'checkbox', onChange: this.checkboxHandler },
      cellProps: { collapsing: true },
    }
    const minIndex = (this.state.activePage - 1) * ROWS_PER_PAGE
    const maxIndex = minIndex + ROWS_PER_PAGE
    return (
      fields.map((record, i) => {
        return (i < minIndex || i >= maxIndex) ? null : (
          <Table.Row
            key={record}
            active={(this.props.isActiveRow || false) && this.props.isActiveRow(this.props.records[i])}
          >
            {[checkboxField, ...this.props.fields].map(field =>
              <Table.Cell key={`${record}-${field.field}`} {...field.cellProps} >
                <Field name={`${record}.${field.field}`} {...field.fieldProps} />
              </Table.Cell>,
            )}
          </Table.Row>
        )
      })
    )
  }

  formContent = () => {
    return (
      <div style={{ marginBottom: this.props.records.length > ROWS_PER_PAGE ? '50px' : '0px' }}>
        <Table basic="very" compact="very">
          <Table.Header>
            <Table.Row>
              <TableHeaderCell key="headerCheckbox">
                <Field name="allChecked" component="input" type="checkbox" onClick={this.headerCheckboxHandler} />
              </TableHeaderCell >
              {this.props.fields.map(field =>
                <TableHeaderCell key={field.header}>
                  {field.header}
                </TableHeaderCell>,
              )}
            </Table.Row>
          </Table.Header>
          <Table.Body>
            <FieldArray
              name="records"
              component={this.renderRow}
            />
          </Table.Body>
        </Table>
        <Divider />
        {this.props.records.length > ROWS_PER_PAGE &&
          <div style={{ marginRight: '20px', float: 'right' }}>
            Showing rows {((this.state.activePage - 1) * ROWS_PER_PAGE) + 1}-
            {Math.min(this.state.activePage * ROWS_PER_PAGE, this.props.records.length)} &nbsp;
            <Pagination
              activePage={this.state.activePage}
              totalPages={Math.ceil(this.props.records.length / ROWS_PER_PAGE)}
              onPageChange={(event, { activePage }) => this.setState({ activePage })}
              size="mini"
            />
          </div>
        }
      </div>
    )
  }

  render() {
    const initialValues = { records: this.props.records }
    return (
      <ReduxFormWrapper
        form={this.props.formName}
        modalName={this.props.modalName}
        submitButtonText="Apply"
        onSubmit={this.handleSubmit}
        confirmCloseIfNotSaved
        closeOnSuccess
        showErrorPanel
        size="small"
        initialValues={initialValues}
        secondarySubmitButton={<DeleteButton>Deleted Selected</DeleteButton>}
        onSecondarySubmit={this.handleDelete}
        renderChildren={this.formContent}
      />
    )
  }

  headerCheckboxHandler = (event) => {
    const editedRecords = this.props.editedRecords.map(record => Object.assign(record, { toDelete: event.target.checked }))
    this.props.changeField(
      'records', editedRecords.slice((this.state.activePage - 1) * ROWS_PER_PAGE, this.state.activePage * ROWS_PER_PAGE),
    )
  }

  checkboxHandler = () => {
    this.props.changeField('allChecked', false)
  }

  handleSubmit = (values) => {
    const editableFields = this.props.fields.map(field => field.field)
    const changedRecords = values.records.filter(
      (record, i) => editableFields.some(field => get(record, field) !== get(this.props.records[i], field)),
    )

    console.log(`${this.props.formName} - handleSubmit:`)
    console.log(changedRecords)

    return this.props.onSubmit({ records: changedRecords })
  }

  handleDelete = (values) => {
    const toDelete = values.records.filter(record => record.toDelete)
    console.log(`${this.props.formName} - handleDelete:`)
    console.log(toDelete)
    this.props.onSubmit({ records: toDelete, delete: true })
  }
}

const mapStateToProps = (state, ownProps) => ({
  editedRecords: formValueSelector(ownProps.formName)(state, 'records') || ownProps.records,
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    changeField: (field, value) => {
      dispatch(change(ownProps.formName, field, value))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(EditRecordsForm)
