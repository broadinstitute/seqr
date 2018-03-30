import React from 'react'
import PropTypes from 'prop-types'
import styled, { injectGlobal } from 'styled-components'
import { connect } from 'react-redux'
import { Table, Divider } from 'semantic-ui-react'
import { Field, FieldArray, formValueSelector } from 'redux-form'

import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'

/* eslint-disable no-unused-expressions */
injectGlobal`
  
  .ui.table.basic.compact td { 
    border-top: 0px !important; 
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

// const DeleteButtonContainer = styled.div`
//   margin: 20px 20px 5px 20px !important;
//   font-size: 1.1em;
//   font-weight: 500;
//   width: 300px;
// `

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

    /* Array of fields to show for a given record row */
    fields: PropTypes.arrayOf(PropTypes.object).isRequired,

    /* Unique identifier for the form */
    formName: PropTypes.string.isRequired,

    onSubmit: PropTypes.func.isRequired,
    onClose: PropTypes.func,
  }

  renderRow = ({ fields }) =>
    fields.map(record =>
      <Table.Row key={record}>
        {[{ field: 'toDelete', fieldProps: { component: 'input', type: 'checkbox' }, cellProps: { collapsing: true } }, ...this.props.fields].map(field =>
          <Table.Cell key={`${record}-${field.field}`} {...field.cellProps} >
            <Field name={`${record}.${field.field}`} {...field.fieldProps} />
          </Table.Cell>,
        )}
      </Table.Row>,
    )

  render() {
    return (
      <ReduxFormWrapper
        form={this.props.formName}
        submitButtonText="Apply"
        onSubmit={this.handleSubmit}
        confirmCloseIfNotSaved
        closeOnSuccess
        showErrorPanel
        handleClose={this.props.onClose}
        size="small"
        initialValues={{ records: this.props.records }}
        secondarySubmitButton={<DeleteButton>Deleted Selected</DeleteButton>}
        onSecondarySubmit={this.handleDelete}
      >
        <Table basic="very" compact="very">
          <Table.Header>
            <Table.Row>
              <Table.HeaderCell key="headerCheckbox" style={{ paddingBottom: '8px' }}>
                <Field name="allChecked" component="input" type="checkbox" />
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

  headerCheckboxHandler = (isChecked) => {
    if (isChecked) {
      //TODO
    } else {
      //TODO
    }
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

export default connect(mapStateToProps)(EditRecordsForm)
