/* eslint-disable no-restricted-globals */

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import EditRecordsForm from 'shared/components/form/EditRecordsForm'
import {
  getProject,
  getFamiliesByGuid,
  getIndividualsByGuid,
  updateFamiliesByGuid,
  updateIndividualsByGuid,
} from 'shared/utils/redux/commonDataActionsAndSelectors'
import styled from 'styled-components'

const TableCell = styled.div`
  margin: 3px 7px;
`

const FamilyIdCell = TableCell.extend`
  width: 8.5em;
  min-width: 7em;
`

const FamilyDescriptionCell = TableCell.extend`
  width: 70%;
  min-width: 7em;
`

const TextInput = styled.input.attrs({
  type: 'text',
})`
  padding: 5px 7px !important;
`


class EditFamiliesForm extends React.Component
{
  static propTypes = {
    //user: PropTypes.object.isRequired,
    project: PropTypes.object.isRequired,
    familiesByGuid: PropTypes.object.isRequired,
    //individualsByGuid: PropTypes.object.isRequired,
    updateFamiliesByGuid: PropTypes.func.isRequired,
    //updateIndividualsByGuid: PropTypes.func.isRequired,
    onSave: PropTypes.func,
    onClose: PropTypes.func,
  }

  constructor(props) {
    super(props)

    // keep track of modified form values instead of refs so that form inputs don't have to all be traversed at submit time.
    // this is a variation of uncontrolled components (https://reactjs.org/docs/uncontrolled-components.html)
    this.modifiedFamiliesByGuid = {}
  }

  computeRowStyle = () => {
    return {}
  }

  renderHeader = () => (
    [
      <FamilyIdCell key={1}>Family Id</FamilyIdCell>,
      <FamilyDescriptionCell key={2}>Family Description</FamilyDescriptionCell>,
    ]
  )

  renderRow = (familyGuid) => {
    const family = this.props.familiesByGuid[familyGuid]

    return (
      [
        <FamilyIdCell key={1}>
          {`${family.familyId}`}
        </FamilyIdCell>,
        <FamilyDescriptionCell key={2}>
          <TextInput
            defaultValue={family.description}
            onChange={e => this.inputChangeHandler(familyGuid, 'description', e.target.value)}
          />
        </FamilyDescriptionCell>,
      ]
    )
  }

  render() {
    return (
      <EditRecordsForm
        recordIds={Object.keys(this.props.familiesByGuid)}
        formSubmitUrl={`/api/project/${this.props.project.projectGuid}/edit_families`}
        deleteRecordsUrl={`/api/project/${this.props.project.projectGuid}/delete_families`}
        renderHeaderCells={this.renderHeader}
        renderTableCells={this.renderRow}
        computeRowStyle={this.computeRowStyle}
        performClientSideValidation={this.performValidation}
        getFormDataJson={() => ({
          modifiedFamilies: this.modifiedFamiliesByGuid,
        })}
        onFormSaveSuccess={this.handleFormSave}
        onDeleteRequestSuccess={this.handleDeleteRequestSuccess}
        onClose={this.handleFormClose}
      />)
  }

  inputChangeHandler = (familyGuid, key, value) => {
    //console.log('setting', key, value)
    if (this.modifiedFamiliesByGuid[familyGuid] === undefined) {
      //edit_individuals API requires familyId and individualId fields to be included
      const family = this.props.familiesByGuid[familyGuid]

      this.modifiedFamiliesByGuid[familyGuid] = {
        familyId: family.familyId,
      }
    }
    this.modifiedFamiliesByGuid[familyGuid][key] = value
  }

  performValidation = () => {
    return { errors: [], warnings: [], info: [] }
  }

  handleFormSave = (responseJson) => {
    console.log('EditIndividualsForm - handleFormSave: ', responseJson)

    this.props.updateFamiliesByGuid(responseJson.familiesByGuid)

    if (this.props.onSave) {
      this.props.onSave(responseJson)
    }

    if (this.props.onClose) {
      this.props.onClose()
    }
  }

  handleFormClose = () => {
    this.props.onClose()
  }

  handleDeleteRequestSuccess = (responseJson) => {
    console.log('delete request - response: ', responseJson)

    location.reload()

    //this.props.updateIndividualsByGuid(responseJson.individualsByGuid)
    //this.props.updateFamiliesByGuid(responseJson.familiesByGuid)
  }

  handleDeleteRequestError = (exception) => {
    console.error('Exception in HttpRequestHelper:', exception)
  }
}

export { EditFamiliesForm as EditFamiliesFormComponent }

const mapStateToProps = state => ({
  project: getProject(state),
  familiesByGuid: getFamiliesByGuid(state),
  individualsByGuid: getIndividualsByGuid(state),
})

const mapDispatchToProps = {
  updateFamiliesByGuid,
  updateIndividualsByGuid,
}

export default connect(mapStateToProps, mapDispatchToProps)(EditFamiliesForm)
