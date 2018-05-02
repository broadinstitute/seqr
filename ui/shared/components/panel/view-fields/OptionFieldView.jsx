import React from 'react'
import PropTypes from 'prop-types'

import { Select } from '../../form/Inputs'
import BaseFieldView from './BaseFieldView'

const OptionFieldView = ({ initialValues, field, idField, tagOptions, fieldDisplay, tagAnnotation, formFieldProps = {}, additionalEditFields = [], ...props }) => {

  let currCategory = null
  const tagSelectOptions = tagOptions.reduce((acc, tag) => {
    if (tag.category !== currCategory) {
      currCategory = tag.category
      if (tag.category) {
        acc.push({ text: tag.category, disabled: true })
      }
    }
    acc.push({ value: tag.value || tag.name, text: tag.name, color: tag.color })
    return acc
  }, [])

  return (
    <BaseFieldView
      modalId={`tags:${initialValues[idField]}-${field}`}
      initialValues={initialValues}
      formFields={[
        {
          name: field,
          options: tagSelectOptions,
          component: Select,
          ...formFieldProps,
        },
        ...additionalEditFields,
      ]}
      fieldId={field}
      fieldDisplay={fieldDisplay || ((value) => {
        const valueConfig = tagSelectOptions.find(option => option.value === value)
        const annotation = tagAnnotation ? tagAnnotation(valueConfig) : null
        return <span>{annotation}{valueConfig.text}</span>
      })}
      {...props}
    />
  )
}

OptionFieldView.propTypes = {
  field: PropTypes.string.isRequired,
  idField: PropTypes.string.isRequired,
  initialValues: PropTypes.object.isRequired,
  tagOptions: PropTypes.array.isRequired,
  tagAnnotation: PropTypes.func,
  additionalEditFields: PropTypes.array,
  formFieldProps: PropTypes.object,
  fieldDisplay: PropTypes.func,
}

export default OptionFieldView
