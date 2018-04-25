import React from 'react'
import PropTypes from 'prop-types'
import { Label, Popup, Icon, Form } from 'semantic-ui-react'
import { Field } from 'redux-form'

import { HorizontalSpacer } from '../../Spacers'
import ReduxFormWrapper from '../../form/ReduxFormWrapper'
import { Multiselect } from '../../form/Inputs'
import Modal from '../../modal/Modal'

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


const TagFieldView = ({ initialValues, field, idField, tagOptions, popupContent, tagAnnotation, onSubmit, editMetadata, hiddenTags = [] }) => {
  const formName = `$tags:${initialValues[idField]}-${field}}`
  const fieldValues = initialValues[field]

  tagOptions = tagOptions.map((tag) => {
    return { ...tag, ...fieldValues.find(val => val.name === tag.name) }
  })
  const tagOptionsMap = tagOptions.reduce((acc, tag) => {
    return { [tag.name]: tag, ...acc }
  }, {})

  let currCategory = null
  const tagSelectOptions = tagOptions.reduce((acc, tag) => {
    if (tag.category !== currCategory) {
      currCategory = tag.category
      if (tag.category) {
        acc.push({ text: tag.category, disabled: true })
      }
    }
    acc.push({ value: tag.name, color: tag.color })
    return acc
  }, [])

  const formFields = [{
    name: field,
    options: tagSelectOptions,
    component: Multiselect,
    placeholder: 'Variant Tags',
    normalize: (value, previousValue, allValues, previousAllValues) => value.map(option => previousAllValues[field].find(prevFieldValue => prevFieldValue.name === option) || tagOptionsMap[option]),
    format: options => options.map(tag => tag.name),
  }]
  if (editMetadata) {
    formFields.push({
      name: field,
      key: 'test',
      isArrayField: true,
      validate: (val) => { return (!val || val.category === NOTES_CATEGORY || val.metadata) ? undefined : 'Required' },
      component: MetadataField,
    })
  }

  return (
    <span>
      {fieldValues.filter(tag => !hiddenTags.includes(tag.name)).map(tag =>
        <span key={tag.name}>
          <HorizontalSpacer width={5} />
          {popupContent && <Popup
            position="top center"
            size="tiny"
            trigger={
              <Label size="small" style={{ color: 'white', backgroundColor: tag.color }} horizontal>{tag.name}</Label>
            }
            header="Tagged by"
            content={popupContent(tag)}
          />}
          {tagAnnotation && <span>{tagAnnotation(tag)}<HorizontalSpacer width={5} /></span>}
        </span>,
      )}
      <HorizontalSpacer width={5} />
      <Modal trigger={<a role="button"><Icon link name="write" /></a>} title="Edit Variant Tags" modalName={formName}>
        <ReduxFormWrapper
          initialValues={{ ...initialValues, [field]: fieldValues.map(tag => tagOptionsMap[tag.name]) }}
          onSubmit={onSubmit}
          form={formName}
          fields={formFields}
        />
      </Modal>
    </span>
  )
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
