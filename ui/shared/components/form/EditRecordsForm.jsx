import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'

import { closeModal } from 'redux/utils/modalReducer'
import DeleteButton from '../buttons/DeleteButton'
import DataTable from '../table/DataTable'
import FormWrapper from './FormWrapper'

const ROWS_PER_PAGE = 12

const TableContainer = styled.div`

  padding: 0 1em;
  
  .ui.table.basic.compact th {
    padding-bottom: 8px;
  }

  .ui.table.basic.compact td {
    border-top: 0px !important;
    overflow: visible;
  }

  .ui.table.basic.compact input[type="text"] {
    padding: 5px 7px;
  }
  
  .ui.table.basic.compact .inline.fields {
    margin: 0 7px;
    
    .field {
      padding-right: 8px;
    }
    
    label {
      padding-left: 18px;
    }
  }

`

const FormContentContainer = styled.div`
  marginBottom: ${props => (props.records && props.records.length > ROWS_PER_PAGE ? '50px' : '0px')};
`

class EditRecordsForm extends React.PureComponent {

  static propTypes = {
    /* Object of records to be edited in this form */
    records: PropTypes.object.isRequired,

    /* The unique identifier key for the record objects */
    idField: PropTypes.string.isRequired,

    entityKey: PropTypes.string.isRequired,

    /* Array of fields to show for a given record row */
    columns: PropTypes.arrayOf(PropTypes.object).isRequired,

    /* Unique identifier for the modal containing the form */
    modalName: PropTypes.string,

    /* Column for filtering displayed table rows */
    filterColumn: PropTypes.string,

    onSubmit: PropTypes.func.isRequired,
    closeParentModal: PropTypes.func.isRequired,
  }

  static defaultProps = {
    modalName: null,
    filterColumn: null,
  }

  state = { data: null }

  checkboxHandler = (newValues) => {
    const { data } = this.state
    const { records } = this.props
    this.setState({
      data: Object.entries(data || records).reduce((acc, [recordId, record]) => (
        { ...acc, [recordId]: { ...record, toDelete: newValues[recordId] } }
      ), {}),
    })
  }

  getFilteredRecords = (values, filterFunc) => {
    const { entityKey } = this.props
    return { [entityKey]: Object.values(values).filter(filterFunc) }
  }

  submitRecords = (values) => {
    const { records, onSubmit, idField, columns } = this.props
    return onSubmit(this.getFilteredRecords(values, record => columns.map(field => field.name).some(
      field => record[field] !== records[record[idField]][field],
    )))
  }

  render() {
    const {
      modalName, records, onSubmit, entityKey, closeParentModal, idField, columns, filterColumn, ...tableProps
    } = this.props
    const { data } = this.state
    const recordData = data || records

    const rowsToDelete = Object.entries(recordData).reduce((acc, [recordId, { toDelete }]) => (
      { ...acc, [recordId]: toDelete }
    ), {})

    const getRowFilterVal = filterColumn ? row => row[filterColumn] : null

    return (
      <FormContentContainer>
        <FormWrapper
          modalName={modalName}
          submitButtonText="Apply"
          onSubmit={this.submitRecords}
          confirmCloseIfNotSaved
          closeOnSuccess
          showErrorPanel
          size="small"
          initialValues={records}
        >
          <TableContainer>
            <DataTable
              compact="very"
              basic="very"
              fixed
              data={Object.values(recordData)}
              selectedRows={rowsToDelete}
              selectRows={this.checkboxHandler}
              columns={columns}
              idField={idField}
              rowsPerPage={ROWS_PER_PAGE}
              footer={
                <DeleteButton
                  initialValues={this.getFilteredRecords(recordData, record => record.toDelete)}
                  onSubmit={onSubmit}
                  onSuccess={closeParentModal}
                  confirmDialog={`Are you sure you want to delete the selected ${entityKey}?`}
                  buttonText="Deleted Selected"
                />
              }
              getRowFilterVal={getRowFilterVal}
              {...tableProps}
            />
          </TableContainer>
        </FormWrapper>
      </FormContentContainer>
    )
  }

}

const mapDispatchToProps = (dispatch, ownProps) => ({
  closeParentModal: () => {
    dispatch(closeModal(ownProps.modalName, true))
  },
})

export default connect(null, mapDispatchToProps)(EditRecordsForm)
