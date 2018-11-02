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
  
  a {
    font-size: 1.1em;
    font-weight: 500;
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

    onSubmit: PropTypes.func.isRequired,
    closeParentModal: PropTypes.func,
  }

  constructor(props) {
    super(props)
    this.state = {
      // activePage: 1,
      data: props.records,
    }
  }

  // TODO pagination?
  // const minIndex = (this.state.activePage - 1) * ROWS_PER_PAGE
  //   const maxIndex = minIndex + ROWS_PER_PAGE
  // <Divider />
  //       {this.props.records.length > ROWS_PER_PAGE &&
  //         <div style={{ marginRight: '20px', float: 'right' }}>
  //           Showing rows {((this.state.activePage - 1) * ROWS_PER_PAGE) + 1}-
  //           {Math.min(this.state.activePage * ROWS_PER_PAGE, this.props.records.length)} &nbsp;
  //           <Pagination
  //             activePage={this.state.activePage}
  //             totalPages={Math.ceil(this.props.records.length / ROWS_PER_PAGE)}
  //             onPageChange={(event, { activePage }) => this.setState({ activePage })}
  //             size="mini"
  //           />
  //         </div>

  render() {
    const { formName, modalName, records, onSubmit, entityKey, closeParentModal, idField, columns, ...tableProps } = this.props

    const rowsToDelete = Object.entries(this.state.data).reduce((acc, [recordId, { toDelete }]) => (
      { ...acc, [recordId]: toDelete }
    ), {})

    const submitRecords = filterFunc => values => onSubmit({ [entityKey]: Object.values(values).filter(filterFunc) })
    const isChangedRecord = record => columns.map(field => field.name).some(
      field => record[field] !== records[record[idField]][field],
    )

    return (
      <FormContentContainer>
        <ReduxFormWrapper
          form={formName}
          modalName={modalName}
          submitButtonText="Apply"
          onSubmit={submitRecords(isChangedRecord)}
          confirmCloseIfNotSaved
          closeOnSuccess
          showErrorPanel
          size="small"
          initialValues={records}
          renderChildren={() =>
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
                {...tableProps}
              />
              <DeleteButton
                initialValues={this.state.data}
                onSubmit={submitRecords(record => record.toDelete)}
                onSuccess={closeParentModal}
                confirmDialog={`Are you sure you want to delete the selected ${entityKey}?`}
                buttonText="Deleted Selected"
              />
            </TableContainer>
          }
        />
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
      dispatch(closeModal(ownProps.modalName))
    },
  }
}

export default connect(null, mapDispatchToProps)(EditRecordsForm)
