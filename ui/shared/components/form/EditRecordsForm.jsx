import React from 'react'
import PropTypes from 'prop-types'
import styled, { injectGlobal } from 'styled-components'
import { connect } from 'react-redux'
import { Table, Divider } from 'semantic-ui-react'
import { Field, FieldArray, formValueSelector, change } from 'redux-form'

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

const TableBodyWindow = styled(Table.Body)`
  max-height: 500px;
  overflow-y: auto;
`

const DeleteButton = styled.a.attrs({ role: 'button', tabIndex: '0' })`
  cursor: pointer;
  margin: 20px 20px 5px 20px !important;
  font-size: 1.1em;
  font-weight: 500;
`

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

  renderRow = ({ fields }) => {
    const checkboxField = {
      field: 'toDelete',
      fieldProps: { component: 'input', type: 'checkbox', onChange: this.checkboxHandler },
      cellProps: { collapsing: true },
    }
    return (
      fields.map((record, i) =>
        <Table.Row
          key={record}
          active={(this.props.isActiveRow || false) && this.props.isActiveRow(this.props.records[i])}
        >
          {[checkboxField, ...this.props.fields].map(field =>
            <Table.Cell key={`${record}-${field.field}`} {...field.cellProps} >
              <Field name={`${record}.${field.field}`} {...field.fieldProps} />
            </Table.Cell>,
          )}
        </Table.Row>,
      )
    )
  }

  render() {
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
        initialValues={{ records: this.props.records }}
        secondarySubmitButton={<DeleteButton>Deleted Selected</DeleteButton>}
        onSecondarySubmit={this.handleDelete}
      >
        <Table basic="very" compact="very">
          <Table.Header>
            <Table.Row>
              <Table.HeaderCell key="headerCheckbox" style={{ paddingBottom: '8px' }}>
                <Field name="allChecked" component="input" type="checkbox" onClick={this.headerCheckboxHandler} />
              </Table.HeaderCell >
              {this.props.fields.map(field =>
                <Table.HeaderCell key={field.header} style={{ paddingBottom: '8px' }}>
                  {field.header}
                </Table.HeaderCell>,
              )}
            </Table.Row>
          </Table.Header>
          <TableBodyWindow>
            <FieldArray
              name="records"
              component={this.renderRow}
            />
          </TableBodyWindow>
        </Table>
        <Divider />
      </ReduxFormWrapper>
    )
  }

  headerCheckboxHandler = (event) => {
    this.props.changeField(
      'records', this.props.editedRecords.map(record => Object.assign(record, { toDelete: event.target.checked })),
    )
  }

  checkboxHandler = () => {
    this.props.changeField('allChecked', false)
  }

  handleSubmit = (values) => {
    const editableFields = this.props.fields.map(field => field.field)
    const changedRecords = values.records.filter(
      (record, i) => editableFields.some(field => record[field] !== this.props.records[i][field]),
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
  editedRecords: formValueSelector(ownProps.formName)(state, 'records'),
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    changeField: (field, value) => {
      dispatch(change(ownProps.formName, field, value))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(EditRecordsForm)
