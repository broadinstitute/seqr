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

const BASE_FORM_ID = '-addVariant'
const CHROMOSOMES = [...Array(23).keys(), 'X', 'Y'].map(val => val.toString()).splice(1)
const ZYGOSITY_OPTIONS = [{ value: 0, name: 'Hom Ref' }, { value: 1, name: 'Het' }, { value: 2, name: 'Hom Alt' }]

const SV_FIELD_NAME = 'svName'
const GENE_ID_FIELD_NAME = 'geneId'
const TRANSCRIPT_ID_FIELD_NAME = 'mainTranscriptId'
const HGVSC_FIELD_NAME = 'hgvsc'
const HGVSP_FIELD_NAME = 'hgvsp'
const TAG_FIELD_NAME = 'tags'
const FORMAT_RESPONSE_FIELDS = [
  GENE_ID_FIELD_NAME, HGVSC_FIELD_NAME, HGVSP_FIELD_NAME, TAG_FIELD_NAME,
]

const ZygosityInput = React.memo(({ individuals, name, title, individualField, error }) =>
  <FormSection name={name}>
    <Divider horizontal>{title}</Divider>
    <Grid columns="equal">
      {individuals.map((({ individualGuid, displayName }) =>
        <Grid.Column key={individualGuid}>
          {configuredField({
            name: individualGuid,
            label: displayName,
            error,
            ...individualField,
          })}
        </Grid.Column>
      ))}
    </Grid>
  </FormSection>,
)

ZygosityInput.propTypes = {
  individuals: PropTypes.array,
  name: PropTypes.string,
  title: PropTypes.string,
  error: PropTypes.bool,
  individualField: PropTypes.object,
}

const mapZygosityInputStateToProps = (state, ownProps) => ({
  individuals: getSortedIndividualsByFamily(state)[ownProps.meta.form.split(BASE_FORM_ID)[0]],
})

const mapTagInputStateToProps = (state, ownProps) => {
  const family = getFamiliesByGuid(state)[ownProps.meta.form.split(BASE_FORM_ID)[0]]
  const { variantTagTypes } = getProjectsByGuid(state)[family.projectGuid]
  return {
    options: variantTagTypes.filter(vtt => vtt.name !== NOTE_TAG_NAME).map(
      ({ name, variantTagTypeGuid, ...tag }) => ({ value: name, text: name, ...tag }),
    ),
  }
}

const ZYGOSITY_FIELD = {
  name: 'genotypes',
  width: 16,
  inline: true,
  component: connect(mapZygosityInputStateToProps)(ZygosityInput),
}

const TAG_FIELD = {
  name: TAG_FIELD_NAME,
  label: 'Tags',
  width: 16,
  inline: true,
  includeCategories: true,
  component: connect(mapTagInputStateToProps)(LargeMultiselect),
  format: value => (value || []).map(({ name }) => name),
  normalize: value => (value || []).map(name => ({ name })),
  validate: value => (value && value.length ? undefined : 'Required'),
}

const CHROM_FIELD = {
  name: 'chrom',
  label: 'Chrom',
  component: Select,
  options: CHROMOSOMES.map(value => ({ value })),
  validate: validators.required,
  width: 2,
  inline: true,
}

const POS_FIELD = {
  validate: validators.required, component: IntegerInput, inline: true, width: 7, min: 0,
}
const START_FIELD = { name: 'pos', label: 'Start Position', ...POS_FIELD }
const END_FIELD = { name: 'end', label: 'Stop Position', ...POS_FIELD }

const SV_TYPE_OPTIONS = [
  { value: 'DEL', text: 'Deletion' },
  { value: 'DUP', text: 'Duplication' },
  { value: 'Multiallelic CNV' },
  { value: 'Insertion' },
  { value: 'Inversion' },
  { value: 'Complex SVs' },
  { value: 'Other' },
]

const validateHasTranscriptId = (value, allValues, props, name) => {
  if (!value) {
    return undefined
  }
  return allValues[TRANSCRIPT_ID_FIELD_NAME] ? undefined : `Transcript ID is required to include ${name}`
}

const SNV_FIELDS = [
  {
    name: GENE_ID_FIELD_NAME,
    label: 'Gene',
    validate: validators.required,
    width: 16,
    control: AwesomeBarFormInput,
    categories: ['genes'],
    fluid: true,
    inline: true,
    placeholder: 'Search for gene',
  },
  CHROM_FIELD,
  START_FIELD,
  { ...END_FIELD, validate: null },
  { name: 'ref', label: 'Ref', validate: validators.required, inline: true, width: 8 },
  { name: 'alt', label: 'Alt', validate: validators.required, inline: true, width: 8 },
  { name: TRANSCRIPT_ID_FIELD_NAME, label: 'Transcript ID', inline: true, width: 6 },
  { name: HGVSC_FIELD_NAME, label: 'HGVSC', inline: true, width: 5, validate: validateHasTranscriptId },
  { name: HGVSP_FIELD_NAME, label: 'HGVSP', inline: true, width: 5, validate: validateHasTranscriptId },
  GENOME_VERSION_FIELD,
  TAG_FIELD,
  {
    ...ZYGOSITY_FIELD,
    title: 'Zygosity',
    individualField: {
      options: ZYGOSITY_OPTIONS,
      component: Select,
      normalize: numAlt => ({ numAlt }),
      format: value => (value || {}).numAlt,
    },
  },
].map(field => (
  field.validate && field.validate !== validateHasTranscriptId ? { ...field, label: `${field.label}*` } : field
))

const SV_FIELDS = [
  CHROM_FIELD,
  START_FIELD,
  END_FIELD,
  GENOME_VERSION_FIELD,
  TAG_FIELD,
  { name: SV_FIELD_NAME, validate: validators.required, label: 'SV Name', inline: true, width: 8 },
  {
    name: 'svType',
    label: 'SV Type',
    component: Select,
    options: SV_TYPE_OPTIONS,
    validate: validators.required,
    inline: true,
    width: 8,
  },
  {
    ...ZYGOSITY_FIELD,
    title: 'Copy Number',
    validate: validators.required,
    individualField: {
      component: IntegerInput,
      normalize: cn => ({ cn }),
      format: value => (value || {}).cn,
      min: 0,
      max: 12,
    },
  },
]

const BaseCreateVariantButton = React.memo(({ variantType, family, user, ...props }) => (
  user.isStaff ? <UpdateButton
    key={`manual${variantType}`}
    modalTitle={`Add a Manual ${variantType} for Family ${family.displayName}`}
    modalId={`${family.familyGuid}${BASE_FORM_ID}-${variantType || 'SNV'}`}
    buttonText={`Add Manual ${variantType}`}
    editIconName="plus"
    showErrorPanel
    {...props}
  /> : null
))

BaseCreateVariantButton.propTypes = {
  variantType: PropTypes.string,
  family: PropTypes.object,
  user: PropTypes.object,
  initialValues: PropTypes.object,
  formFields: PropTypes.array,
  onSubmit: PropTypes.func,
}


const mapStateToProps = (state, ownProps) => ({
  user: getUser(state),
  initialValues: getProjectsByGuid(state)[ownProps.family.projectGuid],
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    onSubmit: (values) => {
      const variant = ownProps.formFields.map(({ name }) => name).filter(
        name => !FORMAT_RESPONSE_FIELDS.includes(name),
      ).reduce(
        (acc, name) => ({ ...acc, [name]: values[name] }), {},
      )

      if (variant.svName) {
        variant.variantId = values.svName
      } else {
        variant.variantId = `${values.chrom}-${values.pos}-${values.ref}-${values.alt}`
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

const CreateVariantButton = connect(mapStateToProps, mapDispatchToProps)(BaseCreateVariantButton)


const CreateVariantButtons = React.memo(({ family }) => ([
  <CreateVariantButton key="SNV" family={family} variantType="Variant" formFields={SNV_FIELDS} />,
  <CreateVariantButton key="SV" family={family} variantType="SV" formFields={SV_FIELDS} />,
]))

CreateVariantButtons.propTypes = {
  family: PropTypes.object,
}


export default CreateVariantButtons
