import React, { createElement } from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Field } from 'react-final-form'
import { FieldArray } from 'react-final-form-arrays'
import { Form, Icon, Popup } from 'semantic-ui-react'

export const StyledForm = styled(({ hasSubmitButton, inline, ...props }) => <Form {...props} />)`
  min-height: inherit;
  display: ${props => (props.inline ? 'inline-block' : 'block')};
  padding-bottom: ${props => props.hasSubmitButton && '50px'};
  
  .field.inline {
    display: inline-block;
    padding-right: 1em;
  }
  
  .inline.fields .field:last-child {
    padding-right: 0 !important;
  }
  
`

export const validators = {
  required: value => (value ? undefined : 'Required'),
  requiredBoolean: value => ((value === true || value === false) ? undefined : 'Required'),
  requiredList: value => ((value && value.length > 0) ? undefined : 'Required'),
  requiredEmail: value => (
    /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$/i.test(value) ? undefined : 'Invalid email address'
  ),
}

const renderField = (props) => {
  const { fieldComponent = Form.Input, meta: { touched, invalid }, submitForm, input, ...additionalProps } = props
  const { onChange, ...additionalInput } = input
  const onChangeSubmit = submitForm ? (data) => {
    onChange(data)
    submitForm({ [props.input.name]: data })
  } : onChange
  return createElement(fieldComponent, {
    error: touched && invalid, meta: props.meta, onChange: onChangeSubmit, ...additionalInput, ...additionalProps,
  })
}

renderField.propTypes = {
  fieldComponent: PropTypes.elementType,
  meta: PropTypes.object,
  input: PropTypes.object,
  submitForm: PropTypes.func,
}

export const helpLabel = (label, labelHelp) => (
  labelHelp ? (
    <label>
      {label}
      &nbsp;
      <Popup trigger={<Icon name="question circle outline" />} content={labelHelp} position="top center" size="small" hoverable />
    </label>
  ) : label
)

const removeField = (fields, i) => (e) => {
  e.preventDefault()
  fields.remove(i)
}

const ArrayFieldItem = ({ addArrayElement, addArrayElementProps, arrayFieldName, singleFieldProps, label, fields }) => (
  <div className="field">
    <label>{label}</label>
    {fields.map((fieldPath, i) => (
      <Field
        key={fieldPath}
        name={arrayFieldName ? `${fieldPath}.${arrayFieldName}` : fieldPath}
        removeField={removeField(fields, i)}
        index={i}
        {...singleFieldProps}
      />
    ))}
    {addArrayElement && createElement(addArrayElement, { addElement: fields.push, ...addArrayElementProps })}
  </div>
)

ArrayFieldItem.propTypes = {
  addArrayElement: PropTypes.object,
  addArrayElementProps: PropTypes.object,
  arrayFieldName: PropTypes.string,
  singleFieldProps: PropTypes.object,
  label: PropTypes.string,
  fields: PropTypes.object,
}

export const configuredField = (field, formProps = {}) => {
  const {
    component, name, isArrayField, addArrayElement, addArrayElementProps, arrayFieldName, key, label, labelHelp,
    ...fieldProps
  } = field
  const baseProps = {
    key: key || name,
    name,
  }
  const singleFieldProps = {
    component: renderField,
    fieldComponent: component,
    submitForm: formProps.submitOnChange ? formProps.onSubmit : null,
    label: helpLabel(label, labelHelp),
    data: formProps.formMetaId && { formId: formProps.formMetaId },
    ...fieldProps,
  }
  return isArrayField ? (
    <FieldArray {...baseProps}>
      {({ fields }) => (
        <ArrayFieldItem
          fields={fields}
          addArrayElement={addArrayElement}
          addArrayElementProps={addArrayElementProps}
          arrayFieldName={arrayFieldName}
          singleFieldProps={singleFieldProps}
          label={label}
        />
      )}
    </FieldArray>
  ) : <Field {...baseProps} {...singleFieldProps} />
}

export const configuredFields = props => props.fields.map(field => configuredField(field, props))
