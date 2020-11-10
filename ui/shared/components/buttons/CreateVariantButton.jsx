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
import { GENOME_VERSION_FIELD, NOTE_TAG_NAME } from '../../utils/constants'

const BASE_FORM_ID = '-addVariant'
const CHROMOSOMES = [...Array(23).keys(), 'X', 'Y'].map(val => val.toString()).splice(1)

const ZygosityInput = React.memo(({ individuals, name, error }) =>
  <FormSection name={name}>
    <Divider horizontal>Copy Number</Divider>
    <Grid columns="equal">
      {individuals.map((({ individualGuid, displayName }) =>
        <Grid.Column key={individualGuid}>
          {configuredField({
            name: individualGuid,
            label: displayName,
            component: IntegerInput,
            normalize: cn => ({ cn }),
            format: value => (value || {}).cn,
            min: 0,
            max: 12,
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

const SV_NAME_FIELD = 'svName'
const TAG_FIELD_NAME = 'tags'

const ZYGOSITY_FIELD = {
  name: 'genotypes',
  width: 16,
  inline: true,
  validate: validators.required,
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

const SV_TYPE_OPTIONS = [
  { value: 'DEL', text: 'Deletion' },
  { value: 'DUP', text: 'Duplication' },
  { value: 'Multiallelic CNV' },
  { value: 'Insertion' },
  { value: 'Inversion' },
  { value: 'Complex SVs' },
  { value: 'Other' },
]

const POS_FIELD = {
  validate: validators.required, component: IntegerInput, inline: true, width: 7, min: 0,
}

const SNV_FIELDS = [
  {
    name: 'chrom',
    label: 'Chrom',
    component: Select,
    options: CHROMOSOMES.map(value => ({ value })),
    validate: validators.required,
    width: 2,
    inline: true,
  },
  { name: 'pos', label: 'Start Position', ...POS_FIELD },
  { name: 'end', label: 'Stop Position', ...POS_FIELD },
  GENOME_VERSION_FIELD,
  TAG_FIELD,
  { name: SV_NAME_FIELD, validate: validators.required, label: 'SV Name', inline: true, width: 8 },
  {
    name: 'svType',
    label: 'SV Type',
    component: Select,
    options: SV_TYPE_OPTIONS,
    validate: validators.required,
    inline: true,
    width: 8,
  },
  ZYGOSITY_FIELD,
]

const SV_FIELDS = [...SNV_FIELDS]

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
      const variant = ownProps.formFields.map(({ name }) => name).filter(name => name !== TAG_FIELD_NAME).reduce(
        (acc, name) => ({ ...acc, [name]: values[name] }), {},
      )
      variant.variantId = values.svName
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
