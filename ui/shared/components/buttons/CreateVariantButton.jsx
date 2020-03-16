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

const ZygosityInput = React.memo(({ individuals, name, error }) =>
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
            error,
          })}
        </Grid.Column>
      ))}
    </Grid>
  </FormSection>,
)

ZygosityInput.propTypes = {
  individuals: PropTypes.array,
  name: PropTypes.string,
  error: PropTypes.bool,
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

const SV_NAME_FIELD = 'svName'
const GENE_ID_FIELD_NAME = 'geneId'
const TRANSCRIPT_ID_FIELD_NAME = 'mainTranscriptId'
const HGVSC_FIELD_NAME = 'hgvsc'
const HGVSP_FIELD_NAME = 'hgvsp'
const TAG_FIELD_NAME = 'tags'
const FORMAT_RESPONSE_FIELDS = [
  GENE_ID_FIELD_NAME, HGVSC_FIELD_NAME, HGVSP_FIELD_NAME, TAG_FIELD_NAME, 'divider1', 'divider2',
]

const ZYGOSITY_FIELD = {
  name: 'genotypes',
  width: 16,
  inline: true,
  validate: validators.required,
  component: connect(mapZygosityInputStateToProps)(ZygosityInput),
}

const TAG_FIELD = {
  name: TAG_FIELD_NAME,
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

const validateSVField = (value, allValues, props, name) => {
  if (value) {
    return undefined
  }
  return allValues[SV_NAME_FIELD] ? `${name} is required for SVs` : undefined
}

const validateSnvField = (value, allValues, props, name) => {
  if (value) {
    return undefined
  }
  return allValues[SV_NAME_FIELD] ? undefined : `${name} is required for SNVs`
}

const DividerField = ({ label }) => <Divider horizontal>{label}</Divider>

DividerField.propTypes = {
  label: PropTypes.string,
}

const SV_TYPE_OPTIONS = [
  { value: 'DEL', text: 'Deletion' },
  { value: 'DUP', text: 'Duplication' },
  { value: 'Multiallelic CNV' },
  { value: 'Insertion' },
  { value: 'Inversion' },
  { value: 'Complex SVs' },
  { value: 'Other' },
]

const FIELDS = [
  {
    name: 'chrom',
    label: 'Chrom*',
    component: Select,
    options: CHROMOSOMES.map(value => ({ value })),
    validate: validators.required,
    width: 2,
    inline: true,
  },
  { name: 'pos', label: 'Start Position*', validate: validators.required, component: IntegerInput, inline: true, width: 7 },
  { name: 'pos_end', label: 'Stop Position', component: IntegerInput, inline: true, width: 7 },
  GENOME_VERSION_FIELD,
  TAG_FIELD,
  { name: 'divider1', label: 'SV Fields', component: DividerField },
  { name: SV_NAME_FIELD, label: 'SV Name', inline: true, width: 8 },
  {
    name: 'svType',
    label: 'SV Type',
    component: Select,
    options: SV_TYPE_OPTIONS,
    validate: validateSVField,
    inline: true,
    width: 8,
  },
  { name: 'divider2', label: 'SNV Fields', component: DividerField },
  {
    name: GENE_ID_FIELD_NAME,
    label: 'Gene',
    validate: validateSnvField,
    width: 6,
    control: AwesomeBarFormInput,
    categories: ['genes'],
    fluid: true,
    inline: true,
    placeholder: 'Search for gene',
  },
  { name: 'ref', label: 'Ref', validate: validateSnvField, inline: true, width: 5 },
  { name: 'alt', label: 'Alt', validate: validateSnvField, inline: true, width: 5 },
  { name: TRANSCRIPT_ID_FIELD_NAME, label: 'Transcript ID', inline: true, width: 6 },
  { name: HGVSC_FIELD_NAME, label: 'HGVSC', width: 5, inline: true, validate: validateHasTranscriptId },
  { name: HGVSP_FIELD_NAME, label: 'HGVSP', width: 5, inline: true, validate: validateHasTranscriptId },
  ZYGOSITY_FIELD,
]

const CreateVariantButton = React.memo(({ project, family, user, onSubmit }) => (
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
))

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
      const variant = FIELDS.map(({ name }) => name).filter(name => !FORMAT_RESPONSE_FIELDS.includes(name)).reduce(
        (acc, name) => ({ ...acc, [name]: values[name] }), {},
      )
      variant.variantId = values.svName || `${values.chrom}-${values.pos}-${values.ref}-${values.alt}`
      if (values[GENE_ID_FIELD_NAME]) {
        variant.transcripts = {
          [values[GENE_ID_FIELD_NAME]]: values[TRANSCRIPT_ID_FIELD_NAME] ? [{
            transcriptId: values[TRANSCRIPT_ID_FIELD_NAME],
            [HGVSC_FIELD_NAME]: values[HGVSC_FIELD_NAME],
            [HGVSP_FIELD_NAME]: values[HGVSP_FIELD_NAME],
          }] : [],
        }
      }
      const formattedValues = {
        familyGuid: ownProps.family.familyGuid,
        tags: values[TAG_FIELD_NAME],
        variant,
      }

      return dispatch(updateVariantTags(formattedValues))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(CreateVariantButton)
