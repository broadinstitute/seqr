import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Label, Popup, Form } from 'semantic-ui-react'
import { Field } from 'redux-form'

import { HorizontalSpacer } from '../../Spacers'
import { ColoredLabel } from '../../StyledComponents'
import { Multiselect } from '../../form/Inputs'
import OptionFieldView from './OptionFieldView'

const NOTES_CATEGORY = 'Functional Data'

const MODAL_STYLE = { minHeight: 'calc(90vh - 100px)' }

const LargeMultiselect = styled(Multiselect)`
  .ui.search.dropdown .menu {
    max-height: calc(90vh - 220px);
  }
`

const MetadataLabel = styled(Label).attrs({ size: 'large', pointing: 'right', basic: true })`
  color: ${props => props.color} !important;
  border-color: ${props => props.color} !important;
      white-space: nowrap;
`

const FieldLabel = styled.label`
  white-space: nowrap;
`

const MetadataField = ({ value, name, error }) => {
  const label = <MetadataLabel color={value.color} content={value.name} />
  return (
    <Form.Group inline>
      {value.description ? <Popup trigger={label} content={value.description} /> : label}
      <Field
        name={`${name}.metadata`}
        component={Form.Input}
        label={<FieldLabel>{value.metadataTitle || 'Notes'}</FieldLabel>}
        maxLength={50}
        error={error}
        width={value.category === NOTES_CATEGORY ? 16 : 4}
        type={value.category !== NOTES_CATEGORY ? 'number' : null}
      />
    </Form.Group>
  )
}

MetadataField.propTypes = {
  value: PropTypes.object,
  name: PropTypes.string,
  error: PropTypes.bool,
}


const TagFieldView = ({ initialValues, field, tagOptions, popup, tagAnnotation, editMetadata, ...props }) => {
  const fieldValues = initialValues[field]

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

  const formFieldProps = {
    component: LargeMultiselect,
    placeholder: 'Variant Tags',
    defaultOpen: true,
    normalize: (value, previousValue, allValues, previousAllValues) => value.map(option => previousAllValues[field].find(prevFieldValue => prevFieldValue.name === option) || tagOptionsMap[option]),
    format: options => options.map(tag => tag.name),
  }

  const additionalFields = editMetadata ? [{
    name: field,
    key: 'test',
    isArrayField: true,
    validate: (val) => { return (!val || val.category === NOTES_CATEGORY || val.metadata) ? undefined : 'Required' },
    component: MetadataField,
  }] : []

  return <OptionFieldView
    field={field}
    tagOptions={tagOptions}
    formFieldProps={formFieldProps}
    additionalEditFields={additionalFields}
    initialValues={mappedValues}
    modalStyle={MODAL_STYLE}
    fieldDisplay={displayFieldValues =>
      <span>
        {displayFieldValues.map((tag) => {
          const label = <ColoredLabel size="small" color={tag.color} horizontal content={tag.name || tag.text} />
          return (
            <span key={tag.name}>
              <HorizontalSpacer width={5} />
              {popup ? popup(tag)(label) : label}
              {tagAnnotation && tagAnnotation(tag)}
            </span>
          )
        })}
      </span>
    }
    {...props}
  />
}

TagFieldView.propTypes = {
  field: PropTypes.string.isRequired,
  idField: PropTypes.string.isRequired,
  initialValues: PropTypes.object.isRequired,
  tagOptions: PropTypes.array.isRequired,
  onSubmit: PropTypes.func.isRequired,
  editMetadata: PropTypes.bool,
  popup: PropTypes.func,
  tagAnnotation: PropTypes.func,
}

export default TagFieldView
