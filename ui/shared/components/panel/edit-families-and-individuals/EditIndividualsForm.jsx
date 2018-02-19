/* eslint-disable jsx-a11y/label-has-for */

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

const IndividualIdCell = TableCell.extend`
  width: 10.5em;
  min-width: 10em;
`

const SexCell = TableCell.extend`
  text-align: center; 
  min-width: 12.5em;
`

const AffectedCell = TableCell.extend`
  text-align: center;
  min-width: 14.5em; 
`

const TextInput = styled.input.attrs({
  type: 'text',
})`
  padding: 5px 7px !important;
`

const RadioInput = styled.input.attrs({
  type: 'radio',
})`
  margin: 0 7px;
`

const sexOptions = [
  { value: 'M', text: 'Male' },
  { value: 'F', text: 'Female' },
  { value: 'U', text: '?' },
]

const affectedOptions = [
  { value: 'A', text: 'Affected' },
  { value: 'N', text: 'Unaffected' },
  { value: 'U', text: '?' },
]


class EditIndividualsForm extends React.Component
{
  static propTypes = {
    //user: PropTypes.object.isRequired,
    project: PropTypes.object.isRequired,
    familiesByGuid: PropTypes.object.isRequired,
    individualsByGuid: PropTypes.object.isRequired,
    updateIndividualsByGuid: PropTypes.func.isRequired,
    updateFamiliesByGuid: PropTypes.func.isRequired,
    onSave: PropTypes.func,
    onClose: PropTypes.func,
  }

  constructor(props) {
    super(props)

    // keep track of modified form values instead of refs so that form inputs don't have to all be traversed at submit time.
    // this is a variation of uncontrolled components (https://reactjs.org/docs/uncontrolled-components.html)
    this.modifiedIndividualsByGuid = {}
  }

  computeRowStyle = (individualGuid) => {
    const individual = this.props.individualsByGuid[individualGuid]
    const family = this.props.familiesByGuid[individual.familyGuid]

    if (this.currentRowFamilyId !== family.familyId) {
      this.currentRowFamilyId = family.familyId
      //style.borderTop = '1px solid #CCC'
      this.currentRowHasBackgroundColor = !this.currentRowHasBackgroundColor
    }

    if (this.currentRowHasBackgroundColor) {
      //style.borderLeft = '1px solid #CCC'
      //style.borderRight = '1px solid #CCC'
      return { backgroundColor: '#F3F3F3' }
      //if (index === individualGuids.length - 1) {
      //  style.borderBottom = '1px solid #CCC'
      //}
    }

    return {}
  }

  renderHeader = () => (
    [
      <FamilyIdCell key={1}>Family Id</FamilyIdCell>,
      <IndividualIdCell key={2}>Individual Id</IndividualIdCell>,
      <IndividualIdCell key={3}>Paternal Id</IndividualIdCell>,
      <IndividualIdCell key={4}>Maternal Id</IndividualIdCell>,
      <SexCell key={5}>Sex</SexCell>,
      <AffectedCell key={6}>Affected Status</AffectedCell>,
    ]
  )

  renderRow = (individualGuid) => {
    const individual = this.props.individualsByGuid[individualGuid]
    const family = this.props.familiesByGuid[individual.familyGuid]

    return (
      [
        <FamilyIdCell key={1}>
          <TextInput
            defaultValue={family.familyId}
            onChange={e => this.inputChangeHandler(individualGuid, 'familyId', e.target.value)}
          />
        </FamilyIdCell>,
        <IndividualIdCell key={2}>
          <TextInput
            defaultValue={individual.individualId}
            onChange={e => this.inputChangeHandler(individualGuid, 'individualId', e.target.value)}
          />
        </IndividualIdCell>,
        <IndividualIdCell key={3}>
          <TextInput
            defaultValue={individual.paternalId}
            onChange={e => this.inputChangeHandler(individualGuid, 'paternalId', e.target.value)}
          />
        </IndividualIdCell>,
        <IndividualIdCell key={4}>
          <TextInput
            defaultValue={individual.maternalId}
            onChange={e => this.inputChangeHandler(individualGuid, 'maternalId', e.target.value)}
          />
        </IndividualIdCell>,
        <SexCell key={5}>
          {
            sexOptions.map(sexOption =>
              <label key={sexOption.value}>
                <RadioInput
                  name={`${individualGuid}-sex`}
                  value={sexOption.value}
                  defaultChecked={individual.sex === sexOption.value}
                  onChange={() => this.inputChangeHandler(individualGuid, 'sex', sexOption.value)}
                />
                {sexOption.text}
              </label>)
          }
        </SexCell>,
        <AffectedCell key={6}>
          {
            affectedOptions.map(affectedOption =>
              <label key={affectedOption.value}>
                <RadioInput
                  name={`${individualGuid}-affected`}
                  value={affectedOption.value}
                  defaultChecked={individual.affected === affectedOption.value}
                  onChange={() => this.inputChangeHandler(individualGuid, 'affected', affectedOption.value)}
                />
                {affectedOption.text}
              </label>)
          }
        </AffectedCell>,
      ]
    )
  }

  render() {
    this.currentRowHasBackgroundColor = false //reset alternating row colors

    return (
      <EditRecordsForm
        recordIds={Object.keys(this.props.individualsByGuid)}
        formSubmitUrl={`/api/project/${this.props.project.projectGuid}/edit_individuals`}
        deleteRecordsUrl={`/api/project/${this.props.project.projectGuid}/delete_individuals`}
        renderHeaderCells={this.renderHeader}
        renderTableCells={this.renderRow}
        computeRowStyle={this.computeRowStyle}
        performClientSideValidation={this.performValidation}
        getFormDataJson={() => ({
          modifiedIndividuals: this.modifiedIndividualsByGuid,
        })}
        onFormSaveSuccess={this.handleFormSave}
        onDeleteRequestSuccess={this.handleDeleteRequestSuccess}
        onClose={this.handleFormClose}
      />)
  }


  inputChangeHandler = (individualGuid, key, value) => {
    //console.log('setting', key, value)
    if (this.modifiedIndividualsByGuid[individualGuid] === undefined) {
      //edit_individuals API requires familyId and individualId fields to be included
      const individual = this.props.individualsByGuid[individualGuid]
      const family = this.props.familiesByGuid[individual.familyGuid]

      this.modifiedIndividualsByGuid[individualGuid] = {
        ...individual,
        familyId: family.familyId,
      }
    }
    this.modifiedIndividualsByGuid[individualGuid][key] = value
  }

  performValidation = () => {
    return { errors: [], warnings: [], info: [] }
  }

  handleFormSave = (responseJson) => {
    console.log('EditIndividualsForm - handleFormSave: ', responseJson)

    /**
     * NOTE: families are also updated here because each family object contains a list of
     * individualGuids for the individuals in the family, and these lists have to be updated
     * in case individuals were moved between families.
     */

    this.props.updateIndividualsByGuid(responseJson.individualsByGuid)
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

    /**
     * NOTE: families are also updated here because each family object contains a list of
     * individualGuids for the individuals in the family, and these lists have to be updated
     * to remove deleted individuals.
     */
    this.props.updateFamiliesByGuid(responseJson.familiesByGuid)
    this.props.updateIndividualsByGuid(responseJson.individualsByGuid)
  }
}

export { EditIndividualsForm as EditIndividualsFormComponent }

const mapStateToProps = state => ({
  project: getProject(state),
  familiesByGuid: getFamiliesByGuid(state),
  individualsByGuid: getIndividualsByGuid(state),
})

const mapDispatchToProps = {
  updateIndividualsByGuid,
  updateFamiliesByGuid,
}

export default connect(mapStateToProps, mapDispatchToProps)(EditIndividualsForm)
