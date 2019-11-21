import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { FormSection } from 'redux-form'
import { Grid, Divider } from 'semantic-ui-react'

import { updateFamily } from 'redux/rootReducer'
import { getUser, getProjectsByGuid, getFamiliesByGuid, getSortedIndividualsByFamily } from 'redux/selectors'

import UpdateButton from './UpdateButton'
import { Select, IntegerInput, LargeMultiselect } from '../form/Inputs'
import { validators, configuredField } from '../form/ReduxFormWrapper'
import { AwesomeBarFormInput } from '../page/AwesomeBar'
import { GENOME_VERSION_FIELD, NOTE_TAG_NAME } from '../../utils/constants'

const BASE_FORM_ID = 'addVariant-'
const CHROMOSOMES = [...Array(23).keys(), 'X', 'Y'].splice(1)
const ZYGOSITY_OPTIONS = [{ value: 0, name: 'Hom Ref' }, { value: 1, name: 'Het' }, { value: 2, name: 'Hom Alt' }]

const ZygosityInput = ({ individuals, name }) =>
  <FormSection name={name}>
    <Divider horizontal>Zygosity</Divider>
    <Grid columns="equal">
      {individuals.map((({ individualGuid, displayName }) =>
        <Grid.Column key={individualGuid}>
          {configuredField({
            name: individualGuid,
            label: displayName,
            options: ZYGOSITY_OPTIONS,
            component: Select,
          })}
        </Grid.Column>
      ))}
    </Grid>
  </FormSection>

ZygosityInput.propTypes = {
  individuals: PropTypes.array,
  name: PropTypes.string,
}

const mapZygosityInputStateToProps = (state, ownProps) => ({
  individuals: getSortedIndividualsByFamily(state)[ownProps.meta.form.replace(BASE_FORM_ID, '')],
})

const mapTagInputStateToProps = (state, ownProps) => {
  const family = getFamiliesByGuid(state)[ownProps.meta.form.replace(BASE_FORM_ID, '')]
  const { variantTagTypes } = getProjectsByGuid(state)[family.projectGuid]
  return {
    options: variantTagTypes.filter(vtt => vtt.name !== NOTE_TAG_NAME).map(
      ({ name, variantTagTypeGuid, ...tag }) => ({ value: variantTagTypeGuid, text: name, ...tag }),
    ),
  }
}

const ZYGOSITY_FIELD = {
  name: 'numAlt',
  width: 16,
  inline: true,
  component: connect(mapZygosityInputStateToProps)(ZygosityInput),
}

const TAG_FIELD = {
  name: 'tags',
  label: 'Tags*',
  width: 16,
  inline: true,
  includeCategories: true,
  component: connect(mapTagInputStateToProps)(LargeMultiselect),
  format: value => value || [],
  validate: value => (value && value.length ? undefined : 'Required'),
}

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
].map(field => ({ inline: true, ...field })), GENOME_VERSION_FIELD, TAG_FIELD, ZYGOSITY_FIELD]

const CreateVariantButton = ({ project, family, user, onSubmit }) => (
  user.isStaff ? <UpdateButton
    modalTitle={`Add a Manual Variant for Family ${family.displayName}`}
    modalId={`${BASE_FORM_ID}${family.familyGuid}`}
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
