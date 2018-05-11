import React from 'react'
import PropTypes from 'prop-types'
import { Label, Popup, Form } from 'semantic-ui-react'
import { Field } from 'redux-form'

import { HorizontalSpacer } from '../../Spacers'
import { Multiselect } from '../../form/Inputs'
import OptionFieldView from './OptionFieldView'

const NOTES_CATEGORY = 'Functional Data'

const MetadataField = ({ value, name, error }) => {
  const label =
    <Label style={{ color: value.color, borderColor: value.color, minWidth: 'fit-content' }} size="large" pointing="right" basic>
      {value.name}
    </Label>
  return (
    <Form.Group inline>
      {value.description ? <Popup trigger={label} content={value.description} /> : label}
      <Field
        name={`${name}.metadata`}
        component={Form.Input}
        label={value.metadataTitle || 'Notes'}
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


const TagFieldView = ({ initialValues, field, tagOptions, popupContent, tagAnnotation, editMetadata, hiddenTags = [], ...props }) => {
  const fieldValues = initialValues[field]

  tagOptions = tagOptions.map((tag) => {
    return { ...tag, ...fieldValues.find(val => val.name === tag.name) }
  })
  const tagOptionsMap = tagOptions.reduce((acc, tag) => {
    return { [tag.name]: tag, ...acc }
  }, {})

  return <OptionFieldView
    field={field}
    tagOptions={tagOptions}
    formFieldProps={{
      component: Multiselect,
      placeholder: 'Variant Tags',
      normalize: (value, previousValue, allValues, previousAllValues) => value.map(option => previousAllValues[field].find(prevFieldValue => prevFieldValue.name === option) || tagOptionsMap[option]),
      format: options => options.map(tag => tag.name),
    }}
    additionalEditFields={editMetadata ? [{
      name: field,
      key: 'test',
      isArrayField: true,
      validate: (val) => { return (!val || val.category === NOTES_CATEGORY || val.metadata) ? undefined : 'Required' },
      component: MetadataField,
    }] : []}
    initialValues={{ ...initialValues, [field]: fieldValues.map(tag => tagOptionsMap[tag.name]) }}
    fieldDisplay={displayFieldValues =>
      <span>
        {displayFieldValues.filter(tag => !hiddenTags.includes(tag.name)).map((tag) => {
          const label =
            <Label size="small" style={{ color: 'white', backgroundColor: tag.color }} horizontal>
              {tag.name || tag.text}
            </Label>
          return (
            <span key={tag.name}>
              <HorizontalSpacer width={5} />
              {popupContent ? <Popup
                position="top center"
                size="tiny"
                trigger={label}
                header="Tagged by"
                content={popupContent(tag)}
              /> : label}
              {tagAnnotation && <span>{tagAnnotation(tag)}<HorizontalSpacer width={5} /></span>}
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
  popupContent: PropTypes.func,
  tagAnnotation: PropTypes.func,
  hiddenTags: PropTypes.array,
}

export default TagFieldView
