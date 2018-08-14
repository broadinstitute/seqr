import React from 'react'
import PropTypes from 'prop-types'

import { Select } from '../../form/Inputs'
import BaseFieldView from './BaseFieldView'

const OptionFieldView = ({ field, tagOptions, fieldDisplay, tagAnnotation, compact, formFieldProps = {}, additionalEditFields = [], ...props }) => {

  const tagSelectOptions = tagOptions.map(({ name, ...tag }) => ({ value: name, text: name, ...tag }))

  const fields = [
    ...additionalEditFields,
    {
      name: field,
      options: tagSelectOptions,
      includeCategories: true,
      component: Select,
      ...formFieldProps,
    },
  ]

  return (
    <BaseFieldView
      formFields={fields}
      field={field}
      compact={compact}
      fieldDisplay={fieldDisplay || ((value) => {
        const valueConfig = tagSelectOptions.find(option => option.value === value) || {}
        const annotation = tagAnnotation ? tagAnnotation(valueConfig, compact) : null
        return <span>{annotation}{compact && annotation ? '' : valueConfig.text}</span>
      })}
      {...props}
    />
  )
}

OptionFieldView.propTypes = {
  field: PropTypes.string.isRequired,
  initialValues: PropTypes.object.isRequired,
  tagOptions: PropTypes.array.isRequired,
  tagAnnotation: PropTypes.func,
  additionalEditFields: PropTypes.array,
  formFieldProps: PropTypes.object,
  fieldDisplay: PropTypes.func,
  compact: PropTypes.bool,
}

export default OptionFieldView
