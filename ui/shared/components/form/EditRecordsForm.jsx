import React from 'react'
import PropTypes from 'prop-types'
import FormWrapper from 'shared/components/form/FormWrapper'
import SendRequestButton from 'shared/components/buttons/send-request/SendRequestButton'
import MessagesPanel from 'shared/components/form/MessagesPanel'
import styled from 'styled-components'
//import { logLifecycleMethods } from 'shared/utils/LifecycleMethodsLogger'
//import List from 'react-virtualized/dist/commonjs/List'

const TableWindow = styled.div`
  
`

const TableBodyWindow = styled.div`
  max-height: 500px;
  border-top: 1px solid lightgray;
  border-bottom: 1px solid lightgray;
  overflow-y: auto;
`

const TableContainer = styled.div`
  display: flex;
  flex-direction: column;
`

const TableRow = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
  flex-wrap: wrap;
  padding: 3px 5px;
  
  //&:hover, &[style]:hover {
  //  border: 1px solid gray;
    //background: #EEF8FF !important;  
  //}
`

const TableHeaderRow = TableRow.extend`
  font-weight: 600;
  padding-bottom: 5px; 
`

const CheckboxInput = styled.input.attrs({
  type: 'checkbox',
})`
  cursor: pointer;
  margin: 0px 10px;
`

const DeleteButtonContainer = styled.div`
  margin: 20px 20px 5px 20px !important;
  font-size: 1.1em;
  font-weight: 500;
  width: 300px;
`

const DeleteButton = styled.a.attrs({ role: 'button', tabIndex: '0' })`
  cursor: pointer;
  margin-right: 15px;
`


class EditRecordsForm extends React.Component
{
  static propTypes = {
    /* Array of recordIds for records to be edited in this form */
    recordIds: PropTypes.arrayOf(PropTypes.string).isRequired,

    /* API endpoint where to send POST request with modified form data */
    formSubmitUrl: PropTypes.string.isRequired,

    /* API endpoint where to send POST request with recordIds to delete */
    deleteRecordsUrl: PropTypes.string.isRequired,

    /* Returns a list of table header cell components */
    renderHeaderCells: PropTypes.func.isRequired,

    /* Takes a recordId and returns a list of table cell components for that record */
    renderTableCells: PropTypes.func.isRequired,

    /* Takes a recordId and returns a style object */
    computeRowStyle: PropTypes.func,

    /* Optional function to perform client-side validation */
    performClientSideValidation: PropTypes.func,

    /** Returns the json object to send to the server on form submit */
    getFormDataJson: PropTypes.func.isRequired,

    onFormSaveSuccess: PropTypes.func,
    onDeleteRequestSuccess: PropTypes.func,
    onClose: PropTypes.func,
  }

  static DEFAULT_STATE = {
    errors: [],
    warnings: [],
    info: [],
    uploadedFileId: null,
  }

  constructor(props) {
    super(props)

    this.state = EditRecordsForm.DEFAULT_STATE

    // keep track of which checkboxes are checked so that they don't have to all be traversed at submit time.
    // this is a variation of uncontrolled components (https://reactjs.org/docs/uncontrolled-components.html)
    this.recordIdsToDelete = new Set()
  }

  renderRow = (recordId) => {
    const rowStyle = this.props.computeRowStyle ? this.props.computeRowStyle(recordId) : null

    return (
      <TableRow key={recordId} style={rowStyle}>
        <CheckboxInput
          name="deleteRowCheckbox"
          onChange={e => this.checkboxChangeHandler(recordId, e.target.checked)}
        />
        {this.props.renderTableCells(recordId)}
      </TableRow>)
  }

  render() {
    const form = (
      <FormWrapper
        submitButtonText="Apply"
        formSubmitUrl={this.props.formSubmitUrl}
        confirmCloseIfNotSaved
        getFormDataJson={this.props.getFormDataJson}
        performClientSideValidation={this.props.performClientSideValidation}
        handleSave={this.handleFormSave}
        handleClose={this.props.onClose}
        size="small"
      >
        <TableWindow>
          <TableContainer>
            <TableHeaderRow>
              <CheckboxInput id="headerCheckbox" onChange={e => this.headerCheckboxHandler(e.target.checked)} />
              {this.props.renderHeaderCells()}
            </TableHeaderRow>
          </TableContainer>
          <TableBodyWindow>
            <TableContainer>
              {
                this.props.recordIds.map(this.renderRow)
              }
            </TableContainer>
            {/* <List height={500} width={1000} overscanRowCount={50} rowCount={Object.keys(this.props.individualsByGuid).length} rowHeight={35} noRowsRenderer={this._noRowsRenderer} rowRenderer={this.renderRow} /> */}
          </TableBodyWindow>
        </TableWindow>
        <MessagesPanel errors={this.state.errors} warnings={this.state.warnings} info={this.state.info} />
        <DeleteButtonContainer>
          <SendRequestButton
            button={<DeleteButton>Deleted Selected</DeleteButton>}
            requestUrl={this.props.deleteRecordsUrl}
            showConfirmDialogBeforeSending="Are you sure you want to delete the selected rows?"
            getDataToSend={() => ({ form: { recordIdsToDelete: [...this.recordIdsToDelete] } })}
            onRequestSuccess={this.handleDeleteRequestSuccess}
          />
        </DeleteButtonContainer>
      </FormWrapper>)
    return form
  }

  headerCheckboxHandler = (isChecked) => {
    if (isChecked) {
      this.props.recordIds.forEach((recordId) => {
        this.recordIdsToDelete.add(recordId)
      })
    } else {
      this.recordIdsToDelete.clear()
    }

    [...document.getElementsByName('deleteRowCheckbox')].forEach((checkboxRef) => {
      checkboxRef.checked = isChecked
    })
  }

  checkboxChangeHandler = (recordId, isChecked) => {
    const headerCheckboxRef = document.getElementById('headerCheckbox')
    if (isChecked) {
      headerCheckboxRef.checked = this.recordIdsToDelete.size === this.props.recordIds.length
      this.recordIdsToDelete.add(recordId)
    } else {
      headerCheckboxRef.checked = false
      this.recordIdsToDelete.delete(recordId)
    }
  }

  handleFormSave = (responseJson) => {
    if (responseJson.errors || responseJson.warnings) {
      this.setState({
        errors: responseJson.errors,
        warnings: responseJson.warnings,
      })
    }

    if (responseJson.errors) {
      return
    }

    if (this.props.onFormSaveSuccess) {
      this.props.onFormSaveSuccess(responseJson)
    }
  }

  handleDeleteRequestSuccess = (responseJson) => {
    console.log('delete request - response: ', responseJson)

    if (this.props.onDeleteRequestSuccess) {
      this.props.onDeleteRequestSuccess(responseJson)
    }

    //this.props.onClose()
  }
}

export default EditRecordsForm
