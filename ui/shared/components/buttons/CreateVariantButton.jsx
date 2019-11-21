import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { updateFamily } from 'redux/rootReducer'
import { getUser, getProjectsByGuid } from 'redux/selectors'

import UpdateButton from './UpdateButton'
import { Select, IntegerInput } from '../form/Inputs'
import { validators } from '../form/ReduxFormWrapper'
import { AwesomeBarFormInput } from '../page/AwesomeBar'
import { GENOME_VERSION_FIELD } from '../../utils/constants'

const CHROMOSOMES = [...Array(23).keys(), 'X', 'Y'].splice(1)

const FIELDS = [...[
  {
    name: 'geneId',
    label: 'Gene*',
    validate: validators.required,
    width: 16,
    control: AwesomeBarFormInput,
    categories: ['genes'],
    fluid: true,
    placeholder: 'Search for gene',
  },
  { name: 'zygosity', label: 'Zygosity TODO', width: 16 },
  {
    name: 'chrom',
    label: 'Chrom*',
    component: Select,
    options: CHROMOSOMES.map(value => ({ value })),
    validate: validators.required,
    width: 2,
  },
  { name: 'start', label: 'Start Position*', validate: validators.required, component: IntegerInput, width: 7 },
  { name: 'stop', label: 'Stop Position', component: IntegerInput, width: 7 },
  { name: 'ref', label: 'Ref*', validate: validators.required, width: 8 },
  { name: 'alt', label: 'Alt*', validate: validators.required, width: 8 },
  { name: 'transcriptId', label: 'Transcript ID', width: 6 },
  { name: 'hgvsc', label: 'HGVSC', width: 5 },
  { name: 'hgvsp', label: 'HGVSP', width: 5 },
].map(field => ({ inline: true, ...field })), GENOME_VERSION_FIELD]

const CreateVariantButton = ({ project, family, user, onSubmit }) => (
  user.isStaff ? <UpdateButton
    modalTitle={`Add a Manual Variant for Family ${family.displayName}`}
    modalId={`addVariant-${family.familyGuid}`}
    buttonText="Add Manual Variant"
    editIconName="plus"
    initialValues={project}
    onSubmit={onSubmit}
    formFields={FIELDS}
  /> : null
)

CreateVariantButton.propTypes = {
  project: PropTypes.object,
  family: PropTypes.object,
  user: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  user: getUser(state),
  project: getProjectsByGuid(state)[ownProps.family.projectGuid],
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    onSubmit: (values) => {
      return dispatch(updateFamily({ ...values, familyGuid: ownProps.family.familyGuid, familyField: 'manual_variant' }))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(CreateVariantButton)
