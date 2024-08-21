import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Divider, Accordion } from 'semantic-ui-react'

import { updateVariantTags } from 'redux/rootReducer'
import { getUser, getSortedIndividualsByFamily } from 'redux/selectors'

import UpdateButton from 'shared/components/buttons/UpdateButton'
import { Select, IntegerInput, LargeMultiselect } from 'shared/components/form/Inputs'
import { validators, configuredField } from 'shared/components/form/FormHelpers'
import { AwesomeBarFormInput } from 'shared/components/page/AwesomeBar'
import { GENOME_VERSION_FIELD, SV_TYPES } from 'shared/utils/constants'

import { TAG_FORM_FIELD, TAG_FIELD_NAME } from '../constants'
import { getTaggedVariantsByFamilyType, getProjectTagTypeOptions, getCurrentProject } from '../selectors'
import SelectSavedVariantsTable, { VARIANT_POS_COLUMN, TAG_COLUMN, GENES_COLUMN } from './SelectSavedVariantsTable'

const CHROMOSOMES = [...Array(23).keys(), 'X', 'Y', 'M'].map(val => val.toString()).splice(1)
const ZYGOSITY_OPTIONS = [{ value: 0, name: 'Hom Ref' }, { value: 1, name: 'Het' }, { value: 2, name: 'Hom Alt' }]

const SV_FIELD_NAME = 'svName'
const GENE_ID_FIELD_NAME = 'geneId'
const TRANSCRIPT_ID_FIELD_NAME = 'mainTranscriptId'
const HGVSC_FIELD_NAME = 'hgvsc'
const HGVSP_FIELD_NAME = 'hgvsp'
const VARIANTS_FIELD_NAME = 'variants'
const FORMAT_RESPONSE_FIELDS = [
  GENE_ID_FIELD_NAME, HGVSC_FIELD_NAME, HGVSP_FIELD_NAME, TAG_FIELD_NAME, VARIANTS_FIELD_NAME,
]

const ZygosityInput = React.memo(({ individuals, name, title, individualField, error }) => (
  <div>
    <Divider horizontal>{title}</Divider>
    <Grid columns="equal">
      {individuals.map((({ individualGuid, displayName }) => (
        <Grid.Column key={individualGuid}>
          {configuredField({
            name: `${name}.${individualGuid}`,
            label: displayName,
            error,
            ...individualField,
          })}
        </Grid.Column>
      )))}
    </Grid>
  </div>
))

ZygosityInput.propTypes = {
  individuals: PropTypes.arrayOf(PropTypes.object),
  name: PropTypes.string,
  title: PropTypes.string,
  error: PropTypes.bool,
  individualField: PropTypes.object,
}

const mapZygosityInputStateToProps = (state, ownProps) => ({
  individuals: getSortedIndividualsByFamily(state)[ownProps.meta.data.formId],
})

const mapTagInputStateToProps = state => ({
  options: getProjectTagTypeOptions(state),
})

const accordionPanels = ({ accordionLabel, dispatch, showSVs, ...props }) => ([{
  key: 'mnv',
  title: accordionLabel,
  content: { content: <SelectSavedVariantsTable {...props} /> },
}])

const SavedVariantToggle = props => <Accordion styled fluid panels={accordionPanels(props)} />

const mapSavedVariantsStateToProps = (state, ownProps) => {
  const familyGuid = ownProps.meta.data.formId
  return {
    data: (getTaggedVariantsByFamilyType(state)[familyGuid] || {})[ownProps.showSVs || false],
    familyGuid,
  }
}

const SavedVariantField = connect(mapSavedVariantsStateToProps)(SavedVariantToggle)

const SAVED_VARIANT_COLUMNS = [
  GENES_COLUMN,
  VARIANT_POS_COLUMN,
  TAG_COLUMN,
]
const SAVED_SV_COLUMNS = [{ name: 'svType', content: 'SV Type', width: 2 }, ...SAVED_VARIANT_COLUMNS]

const GENOME_FIELD = { ...GENOME_VERSION_FIELD, inline: false, width: null }

const ZYGOSITY_FIELD = {
  name: 'genotypes',
  component: connect(mapZygosityInputStateToProps)(ZygosityInput),
}

const TAG_FIELD = {
  component: connect(mapTagInputStateToProps)(LargeMultiselect),
  ...TAG_FORM_FIELD,
}

const CHROM_FIELD = {
  name: 'chrom',
  label: 'Chrom',
  component: Select,
  options: CHROMOSOMES.map(value => ({ value })),
  validate: validators.required,
  width: 2,
}

const POS_FIELD = {
  validate: validators.required, component: IntegerInput, width: 7, min: 0,
}
const START_FIELD = { name: 'pos', label: 'Start Position', ...POS_FIELD }
const END_FIELD = { name: 'end', label: 'Stop Position', ...POS_FIELD }

const GENE_FIELD = {
  name: GENE_ID_FIELD_NAME,
  label: 'Gene',
  control: AwesomeBarFormInput,
  categories: ['genes'],
  fluid: true,
  placeholder: 'Search for gene',
}

const SAVED_VARIANT_FIELD = {
  name: VARIANTS_FIELD_NAME,
  idField: 'variantGuid',
  includeSelectedRowData: true,
  control: SavedVariantField,
}

const validateHasTranscriptId = (value, allValues, props, name) => {
  if (!value) {
    return undefined
  }
  return allValues[TRANSCRIPT_ID_FIELD_NAME] ? undefined : `Transcript ID is required to include ${name}`
}

const formatField = (field) => {
  const formattedField = { inline: true, width: 16, ...field }
  if (field.validate && field.validate !== validateHasTranscriptId) {
    formattedField.label = `${field.label}*`
  }
  return formattedField
}

const SNV_FIELDS = [
  CHROM_FIELD,
  START_FIELD,
  { ...END_FIELD, validate: null },
  { name: 'ref', label: 'Ref', validate: validators.required, width: 4 },
  { name: 'alt', label: 'Alt', validate: validators.required, width: 4 },
  { ...GENE_FIELD, width: 8, validate: validators.required },
  { name: TRANSCRIPT_ID_FIELD_NAME, label: 'Transcript ID', width: 6 },
  { name: HGVSC_FIELD_NAME, label: 'HGVSC', width: 5, validate: validateHasTranscriptId },
  { name: HGVSP_FIELD_NAME, label: 'HGVSP', width: 5, validate: validateHasTranscriptId },
  GENOME_FIELD,
  TAG_FIELD,
  { accordionLabel: 'Multinucleotide Variant', columns: SAVED_VARIANT_COLUMNS, ...SAVED_VARIANT_FIELD },
  {
    ...ZYGOSITY_FIELD,
    title: 'Zygosity',
    individualField: {
      options: ZYGOSITY_OPTIONS,
      component: Select,
      parse: numAlt => ({ numAlt }),
      format: value => (value || {}).numAlt,
    },
  },
].map(formatField)

const SV_FIELDS = [
  CHROM_FIELD,
  START_FIELD,
  END_FIELD,
  GENE_FIELD,
  GENOME_FIELD,
  TAG_FIELD,
  { name: SV_FIELD_NAME, validate: validators.required, label: 'SV Name', width: 8 },
  {
    name: 'svType',
    label: 'SV Type',
    component: Select,
    options: SV_TYPES,
    validate: validators.required,
    width: 8,
  },
  { accordionLabel: 'Associated SVs', columns: SAVED_SV_COLUMNS, showSVs: true, ...SAVED_VARIANT_FIELD },
  {
    ...ZYGOSITY_FIELD,
    title: 'Copy Number',
    validate: validators.required,
    individualField: {
      component: IntegerInput,
      parse: cn => ({ cn }),
      format: value => (value || {}).cn,
      min: 0,
      max: 12,
    },
  },
].map(formatField)

const BaseCreateVariantButton = React.memo(({ variantType, family, user, project, ...props }) => (
  (project.isAnalystProject ? user.isAnalyst : project.canEdit) ? (
    <UpdateButton
      key={`manual${variantType}`}
      initialValues={project}
      modalTitle={`Add a Manual ${variantType} for Family ${family.displayName}`}
      modalId={`${family.familyGuid}-addVariant-${variantType || 'SNV'}`}
      formMetaId={family.familyGuid}
      modalSize="large"
      buttonText={`Add Manual ${variantType}`}
      editIconName="plus"
      showErrorPanel
      {...props}
    />
  ) : null
))

BaseCreateVariantButton.propTypes = {
  variantType: PropTypes.string,
  family: PropTypes.object,
  user: PropTypes.object,
  project: PropTypes.object,
  formFields: PropTypes.arrayOf(PropTypes.object),
  onSubmit: PropTypes.func,
}

const mapStateToProps = state => ({
  user: getUser(state),
  project: getCurrentProject(state),
})

const mapDispatchToProps = (dispatch, ownProps) => ({
  onSubmit: (values) => {
    const variant = ownProps.formFields.map(({ name }) => name).filter(
      name => !FORMAT_RESPONSE_FIELDS.includes(name),
    ).reduce(
      (acc, name) => ({ ...acc, [name]: values[name] }), {},
    )

    if (variant.svName) {
      variant.variantId = values.svName
      if (values[GENE_ID_FIELD_NAME]) {
        variant.transcripts = { [values[GENE_ID_FIELD_NAME]]: [] }
      }
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

    const variants = Object.values(values[VARIANTS_FIELD_NAME] || {}).filter(v => v)

    const formattedValues = {
      familyGuid: ownProps.family.familyGuid,
      tags: values[TAG_FIELD_NAME],
      variant: [variant, ...variants],
    }

    return dispatch(updateVariantTags(formattedValues))
  },
})

const CreateVariantButton = connect(mapStateToProps, mapDispatchToProps)(BaseCreateVariantButton)

const CreateVariantButtons = React.memo(({ family }) => ([
  <CreateVariantButton key="SNV" family={family} variantType="Variant" formFields={SNV_FIELDS} />,
  <CreateVariantButton key="SV" family={family} variantType="SV" formFields={SV_FIELDS} />,
]))

CreateVariantButtons.propTypes = {
  family: PropTypes.object,
}

export default CreateVariantButtons
