import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'

import { closeModal } from 'redux/utils/modalReducer'
import DeleteButton from '../buttons/DeleteButton'
import SortableTable from '../table/SortableTable'
import ReduxFormWrapper from './ReduxFormWrapper'

const ROWS_PER_PAGE = 12

/* eslint-disable no-unused-expressions */
const TableContainer = styled.div`

  padding: 0 1em;
  
  .ui.table.basic.compact th {
    padding-bottom: 8px;
  }

  .ui.table.basic.compact td {
    border-top: 0px !important;
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


class EditRecordsForm extends React.Component
{
  static propTypes = {
    /* Object of records to be edited in this form */
    records: PropTypes.object.isRequired,

    /* The unique identifier key for the record objects */
    idField: PropTypes.string,

    isActiveRow: PropTypes.func,
    entityKey: PropTypes.string,

    /* Array of fields to show for a given record row */
    columns: PropTypes.arrayOf(PropTypes.object).isRequired,

    /* Unique identifier for the form */
    formName: PropTypes.string.isRequired,

    /* Unique identifier for the modal containing the form if there are multiple forms in the modal */
    modalName: PropTypes.string,

    /* Column for filtering displayed table rows */
    filterColumn: PropTypes.string,

    onSubmit: PropTypes.func.isRequired,
    closeParentModal: PropTypes.func,
  }

  constructor(props) {
    super(props)
    this.state = {
      data: props.records,
    }
  }


  render() {
    const { formName, modalName, records, onSubmit, entityKey, closeParentModal, idField, columns, filterColumn, ...tableProps } = this.props

    const rowsToDelete = Object.entries(this.state.data).reduce((acc, [recordId, { toDelete }]) => (
      { ...acc, [recordId]: toDelete }
    ), {})

    const getFilteredRecords = (values, filterFunc) => ({ [entityKey]: Object.values(values).filter(filterFunc) })

    const getRowFilterVal = filterColumn ? row => row[filterColumn] : null

    const submitRecords = values =>
      onSubmit(getFilteredRecords(values, record => columns.map(field => field.name).some(
        field => record[field] !== records[record[idField]][field],
      )))

    return (
      <FormContentContainer>
        <ReduxFormWrapper
          form={formName}
          modalName={modalName}
          submitButtonText="Apply"
          onSubmit={submitRecords}
          confirmCloseIfNotSaved
          closeOnSuccess
          showErrorPanel
          size="small"
          initialValues={records}
        >
          <TableContainer>
            <SortableTable
              compact="very"
              basic="very"
              fixed
              data={Object.values(this.state.data)}
              selectedRows={rowsToDelete}
              selectRows={this.checkboxHandler}
              columns={columns}
              idField={idField}
              rowsPerPage={ROWS_PER_PAGE}
              footer={
                <DeleteButton
                  initialValues={getFilteredRecords(this.state.data, record => record.toDelete)}
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
        </ReduxFormWrapper>
      </FormContentContainer>
    )
  }

  checkboxHandler = (newValues) => {
    this.setState({
      data: Object.entries(this.state.data).reduce((acc, [recordId, record]) => (
        { ...acc, [recordId]: { ...record, toDelete: newValues[recordId] } }
      ), {}),
    })
  }
}

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    closeParentModal: () => {
      dispatch(closeModal(ownProps.modalName, true))
    },
  }
}

export default connect(null, mapDispatchToProps)(EditRecordsForm)
