/* eslint-disable jsx-a11y/label-has-for */

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Field } from 'redux-form'

import { updateIndividuals } from 'redux/rootReducer'
import { getProjectIndividualsWithFamily } from 'pages/Project/reducers'
import EditRecordsForm from '../EditRecordsForm'


const sexOptions = [
  { value: 'M', label: 'Male' },
  { value: 'F', label: 'Female' },
  { value: 'U', label: '?' },
]

const affectedOptions = [
  { value: 'A', label: 'Affected' },
  { value: 'N', label: 'Unaffected' },
  { value: 'U', label: '?' },
]

const RadioGroup = (props) => {
  const { input, options } = props
  return options.map(option =>
    <label key={`${input.name}.${option.value}`}>
      <Field component="input" type="radio" style={{ margin: '0 7px' }} {...input} {...option} />
      {option.label}
    </label>,
  )
}


const EditIndividualsForm = (props) => {
  let currFamilyGuid
  let currActive = false
  const familyActiveMap = props.individuals.reduce((acc, ind) => {
    if (ind.familyGuid !== currFamilyGuid) {
      currFamilyGuid = ind.familyGuid
      currActive = !currActive
      acc[ind.familyGuid] = currActive
    }
    return acc
  }, {})

  return (
    <EditRecordsForm
      formName="editIndividuals"
      modalName={props.modalName}
      records={props.individuals}
      fields={[
        {
          header: 'Family Id',
          field: 'family.familyId',
          fieldProps: { component: 'input', type: 'text' },
        },
        {
          header: 'Individual Id',
          field: 'individualId',
          fieldProps: { component: 'input', type: 'text' },
        },
        {
          header: 'Paternal Id',
          field: 'paternalId',
          fieldProps: { component: 'input', type: 'text' },
        },
        {
          header: 'Maternal Id',
          field: 'maternalId',
          fieldProps: { component: 'input', type: 'text' },
        },
        {
          header: 'Sex',
          field: 'sex',
          fieldProps: { component: RadioGroup, options: sexOptions },
          cellProps: { collapsing: true },
        },
        {
          header: 'Affected Status',
          field: 'affected',
          fieldProps: { component: RadioGroup, options: affectedOptions },
          cellProps: { collapsing: true, style: { paddingRight: '30px' } },
        },
      ]}
      onSubmit={({ records, ...values }) => props.updateIndividuals({ individuals: records, ...values })}
      isActiveRow={individual => familyActiveMap[individual.familyGuid]}
    />
  )
}

EditIndividualsForm.propTypes = {
  individuals: PropTypes.array.isRequired,
  updateIndividuals: PropTypes.func.isRequired,
  modalName: PropTypes.string,
}

export { EditIndividualsForm as EditIndividualsFormComponent }

const mapStateToProps = state => ({
  individuals: getProjectIndividualsWithFamily(state),
})

const mapDispatchToProps = {
  updateIndividuals,
}

export default connect(mapStateToProps, mapDispatchToProps)(EditIndividualsForm)
