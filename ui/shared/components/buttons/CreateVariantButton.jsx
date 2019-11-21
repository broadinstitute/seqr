import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { FormSection } from 'redux-form'
import { Grid, Divider } from 'semantic-ui-react'

import { updateVariantTags } from 'redux/rootReducer'
import { getUser, getProjectsByGuid, getFamiliesByGuid, getSortedIndividualsByFamily } from 'redux/selectors'

import UpdateButton from './UpdateButton'
import { Select, IntegerInput, LargeMultiselect } from '../form/Inputs'
import { validators, configuredField } from '../form/ReduxFormWrapper'
import { AwesomeBarFormInput } from '../page/AwesomeBar'
import { GENOME_VERSION_FIELD, NOTE_TAG_NAME } from '../../utils/constants'

const BASE_FORM_ID = 'addVariant-'
const CHROMOSOMES = [...Array(23).keys(), 'X', 'Y'].map(val => val.toString()).splice(1)
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
            normalize: numAlt => ({ numAlt }),
            format: value => (value || {}).numAlt,
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
      ({ name, variantTagTypeGuid, ...tag }) => ({ value: name, text: name, ...tag }),
    ),
  }
}

const GENE_ID_FIELD_NAME = 'geneId'
const TRANSCRIPT_ID_FIELD_NAME = 'mainTranscriptId'
const HGVSC_FIELD_NAME = 'hgvsc'
const HGVSP_FIELD_NAME = 'hgvsp'
const FORMAT_RESPONSE_FIELDS = [
  GENE_ID_FIELD_NAME, HGVSC_FIELD_NAME, HGVSP_FIELD_NAME,
]

const ZYGOSITY_FIELD = {
  name: 'genotypes',
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
  format: value => (value || []).map(({ name }) => name),
  normalize: value => (value || []).map(name => ({ name })),
  validate: value => (value && value.length ? undefined : 'Required'),
}

const validateHasTranscriptId = (value, allValues, props, name) => {
  if (!value) {
    return undefined
  }
  return allValues[TRANSCRIPT_ID_FIELD_NAME] ? undefined : `Transcript ID is required to include ${name}`
}

const FIELDS = [...[
  {
    name: GENE_ID_FIELD_NAME,
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
  { name: 'pos', label: 'Start Position*', validate: validators.required, component: IntegerInput, width: 7 },
  { name: 'pos_end', label: 'Stop Position', component: IntegerInput, width: 7 },
  { name: 'ref', label: 'Ref*', validate: validators.required, width: 8 },
  { name: 'alt', label: 'Alt*', validate: validators.required, width: 8 },
  { name: TRANSCRIPT_ID_FIELD_NAME, label: 'Transcript ID', width: 6 },
  { name: HGVSC_FIELD_NAME, label: 'HGVSC', width: 5, validate: validateHasTranscriptId },
  { name: HGVSP_FIELD_NAME, label: 'HGVSP', width: 5, validate: validateHasTranscriptId },
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
    showErrorPanel
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
      const formattedValues = {
        ...FIELDS.map(({ name }) => name).filter(name => !FORMAT_RESPONSE_FIELDS.includes(name)).reduce(
          (acc, name) => ({ ...acc, [name]: values[name] }), {},
        ),
        familyGuid: ownProps.family.familyGuid,
        variantId: `${values.chrom}-${values.pos}-${values.ref}-${values.alt}`,
        transcripts: {
          [values[GENE_ID_FIELD_NAME]]: values[TRANSCRIPT_ID_FIELD_NAME] ? [{
            transcriptId: values[TRANSCRIPT_ID_FIELD_NAME],
            [HGVSC_FIELD_NAME]: values[HGVSC_FIELD_NAME],
            [HGVSP_FIELD_NAME]: values[HGVSP_FIELD_NAME],
          }] : [],
        },
      }

      return dispatch(updateVariantTags(formattedValues))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(CreateVariantButton)
