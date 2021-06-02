import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup, Form } from 'semantic-ui-react'
import { Field } from 'redux-form'

import { HorizontalSpacer } from '../../Spacers'
import { ColoredLabel, ColoredOutlineLabel } from '../../StyledComponents'
import { LargeMultiselect, Multiselect } from '../../form/Inputs'
import OptionFieldView from './OptionFieldView'

const NOTES_CATEGORY = 'Functional Data'

const MODAL_STYLE = { minHeight: 'calc(90vh - 100px)' }

const MetadataFormGroup = styled(Form.Group).attrs({ inline: true })`
  label, .label {
    white-space: nowrap;
  }
  
  .fluid.selection.dropdown {
    width: 100% !important;
  } 
`

const MultiselectField = ({ input, ...props }) => <Multiselect {...input} {...props} />

MultiselectField.propTypes = {
  input: PropTypes.object,
}

const METADATA_FIELD_PROPS = {
  [NOTES_CATEGORY]: { width: 16, maxLength: 50, placeholder: 'Enter up to 50 characters' },
  Collaboration: { width: 16, maxLength: 50, placeholder: 'Brief reason for excluding. Enter up to 50 characters' },
  'Test Type(s)': {
    width: 16,
    component: MultiselectField,
    fluid: true,
    allowAdditions: true,
    addValueOptions: true,
    options: ['Sanger', 'Segregation', 'SV', 'Splicing'].map(value => ({ value })),
    placeholder: 'Select test types or add your own',
    format: val => (val || '').split(', ').filter(v => v),
    normalize: val => (val || []).join(', '),
  },
}

const MetadataField = React.memo(({ value, name, error }) => {
  if (!value.metadataTitle) {
    return null
  }
  const label = <ColoredOutlineLabel color={value.color} content={value.name} size="large" pointing="right" basic />
  const fieldProps = METADATA_FIELD_PROPS[value.metadataTitle] || METADATA_FIELD_PROPS[value.category] || { width: 4, type: 'number', min: 0 }
  return (
    <MetadataFormGroup>
      {value.description ? <Popup trigger={label} content={value.description} /> : label}
      <Field
        name={`${name}.metadata`}
        component={Form.Input}
        label={value.metadataTitle}
        error={error}
        {...fieldProps}
      />
    </MetadataFormGroup>
  )
})

MetadataField.propTypes = {
  value: PropTypes.object,
  name: PropTypes.string,
  error: PropTypes.bool,
}

export const TagFieldDisplay = React.memo(({ displayFieldValues, tagAnnotation, popup, displayAnnotationFirst, displayMetadata }) => {
  return (
    <span>
      {displayFieldValues.map((tag) => {
        let content = tag.name || tag.text
        if (displayMetadata && tag.metadata) {
          content = `${content}: ${tag.metadata}`
        }
        const label = <ColoredLabel size="small" color={tag.color} horizontal content={content} />
        const annotation = tagAnnotation && tagAnnotation(tag)
        return (
          <span key={tag.tagGuid || tag.name}>
            <HorizontalSpacer width={5} />
            {displayAnnotationFirst && annotation}
            {popup ? popup(tag)(label, displayMetadata) : label}
            {!displayAnnotationFirst && annotation}
          </span>
        )
      })}
    </span>
  )
})

TagFieldDisplay.propTypes = {
  displayFieldValues: PropTypes.array.isRequired,
  popup: PropTypes.func,
  tagAnnotation: PropTypes.func,
  displayAnnotationFirst: PropTypes.bool,
  displayMetadata: PropTypes.bool,
}

const TagFieldView = React.memo(({ simplifiedValue, initialValues, field, tagOptions, popup, tagAnnotation, validate, displayMetadata, ...props }) => {
  const fieldValues = (initialValues || {})[field] || []

  tagOptions = tagOptions.map((tag, i) => {
    return { ...tag, ...fieldValues.find(val => val.name === tag.name), optionIndex: i }
  })

  const tagOptionsMap = tagOptions.reduce((acc, tag) => {
    return { [tag.name]: tag, ...acc }
  }, {})

  const mappedValues = {
    ...initialValues,
    [field]: fieldValues.map(tag => tagOptionsMap[tag.name]).sort((a, b) => a.optionIndex - b.optionIndex),
  }

  const formFieldProps = simplifiedValue ?
    {
      component: LargeMultiselect,
      defaultOpen: true,
    } :
    {
      component: LargeMultiselect,
      defaultOpen: true,
      normalize: (value, previousValue, allValues, previousAllValues) => value.map(option => previousAllValues[field].find(prevFieldValue => prevFieldValue.name === option) || tagOptionsMap[option]),
      format: options => options.map(tag => tag.name),
    }

  if (validate) {
    formFieldProps.validate = validate
  }

  const additionalFields = tagOptions.some(({ metadataTitle }) => metadataTitle) ? [{
    name: field,
    key: 'test',
    isArrayField: true,
    validate: (val) => { return (!val || !val.metadataTitle || val.category === NOTES_CATEGORY || val.metadata) ? undefined : 'Required' },
    component: MetadataField,
  }] : []

  return <OptionFieldView
    field={field}
    tagOptions={tagOptions}
    formFieldProps={formFieldProps}
    additionalEditFields={additionalFields}
    initialValues={simplifiedValue ? initialValues : mappedValues}
    modalStyle={MODAL_STYLE}
    fieldDisplay={displayFieldValues =>
      <TagFieldDisplay displayFieldValues={displayFieldValues} popup={popup} tagAnnotation={tagAnnotation} displayMetadata={displayMetadata} />
    }
    {...props}
  />
})

TagFieldView.propTypes = {
  field: PropTypes.string.isRequired,
  idField: PropTypes.string.isRequired,
  initialValues: PropTypes.object,
  tagOptions: PropTypes.array.isRequired,
  onSubmit: PropTypes.func.isRequired,
  displayMetadata: PropTypes.bool,
  popup: PropTypes.func,
  tagAnnotation: PropTypes.func,
  simplifiedValue: PropTypes.bool,
  validate: PropTypes.func,
}

export default TagFieldView
