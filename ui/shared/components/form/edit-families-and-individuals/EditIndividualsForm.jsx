/* eslint-disable jsx-a11y/label-has-for */

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Field } from 'redux-form'

import { updateIndividuals } from 'pages/Project/reducers'
import { getProjectFamiliesByGuid, getProjectIndividualsByGuid } from 'pages/Project/selectors'
import { SEX_OPTIONS, AFFECTED_OPTIONS } from 'shared/utils/constants'
import EditRecordsForm from '../EditRecordsForm'

const RadioField = styled(Field)`
  margin: 0 7px;
`

const RadioGroup = (props) => {
  const { input, options } = props
  return options.map(option =>
    <label key={`${input.name}.${option.value}`}>
      <RadioField component="input" type="radio" {...input} {...option} />
      {option.label}
    </label>,
  )
}


const EditIndividualsForm = (props) => {
  let currFamilyGuid
  let currActive = false
  const sortedIndividuals = Object.values(props.individualsByGuid).map(
    individual => ({ ...individual, family: props.familiesByGuid[individual.familyGuid] }),
  ).sort((i1, i2) => i1.family.familyId - i2.family.familyId)
  const familyActiveMap = sortedIndividuals.reduce((acc, ind) => {
    if (ind.familyGuid !== currFamilyGuid) {
      currFamilyGuid = ind.familyGuid
      currActive = !currActive
      acc[ind.familyGuid] = currActive
    }
    return acc
  }, {})
  const fields = [
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
      fieldProps: { component: RadioGroup, options: SEX_OPTIONS },
      cellProps: { collapsing: true },
    },
    {
      header: 'Affected Status',
      field: 'affected',
      fieldProps: { component: RadioGroup, options: AFFECTED_OPTIONS },
      cellProps: { collapsing: true, style: { paddingRight: '30px' } },
    },
  ]
  const submitIndividuals = ({ records, ...values }) => props.updateIndividuals({ individuals: records, ...values })
  const isActiveRow = individual => familyActiveMap[individual.familyGuid]

  return (
    <EditRecordsForm
      formName="editIndividuals"
      modalName={props.modalName}
      records={sortedIndividuals}
      fields={fields}
      onSubmit={submitIndividuals}
      isActiveRow={isActiveRow}
    />
  )
}

EditIndividualsForm.propTypes = {
  individualsByGuid: PropTypes.object.isRequired,
  familiesByGuid: PropTypes.object.isRequired,
  updateIndividuals: PropTypes.func.isRequired,
  modalName: PropTypes.string,
}

export { EditIndividualsForm as EditIndividualsFormComponent }

const mapStateToProps = state => ({
  individualsByGuid: getProjectIndividualsByGuid(state),
  familiesByGuid: getProjectFamiliesByGuid(state),
})

const mapDispatchToProps = {
  updateIndividuals,
}

export default connect(mapStateToProps, mapDispatchToProps)(EditIndividualsForm)
