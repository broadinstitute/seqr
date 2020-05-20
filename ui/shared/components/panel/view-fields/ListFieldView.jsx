import React from 'react'
import PropTypes from 'prop-types'
import { Icon } from 'semantic-ui-react'

import BaseFieldView from './BaseFieldView'
import { BaseSemanticInput } from '../../form/Inputs'
import { validators } from '../../form/ReduxFormWrapper'
import { ButtonLink } from '../../StyledComponents'

const RemovableInput = React.memo(({ removeField, itemComponent, ...props }) =>
  React.createElement(itemComponent || BaseSemanticInput, {
    icon: <Icon name="remove" link onClick={removeField} />,
    inputType: 'Input',
    ...props,
  }),
)

RemovableInput.propTypes = {
  removeField: PropTypes.func,
  itemComponent: PropTypes.func,
}

const AddElementButton = React.memo(({ addElement, addElementLabel }) =>
  <ButtonLink
    icon="plus"
    content={addElementLabel}
    onClick={(e) => {
      e.preventDefault()
      addElement()
    }}
  />,
)

AddElementButton.propTypes = {
  addElementLabel: PropTypes.string,
  addElement: PropTypes.func,
}

const ListFieldView = React.memo(({ addElementLabel, initialValues, formFieldProps = {}, itemJoin, itemDisplay, itemKey, ...props }) => {
  const fields = [{
    name: props.field,
    isArrayField: true,
    addArrayElement: AddElementButton,
    addArrayElementProps: { addElementLabel },
    validate: validators.required,
    component: RemovableInput,
    ...formFieldProps,
  }]
  const initialValue = initialValues[props.field]
  const defaultedInitialValues = {
    ...initialValues,
    [props.field]: (initialValue && initialValue.length) ? initialValue : [''],
  }

  const fieldDisplay = values => (itemJoin ? values.join(itemJoin) : values.map(value =>
    <div key={itemKey ? itemKey(value) : value}>{itemDisplay ? itemDisplay(value) : value}</div>,
  ))

  return <BaseFieldView
    formFields={fields}
    initialValues={defaultedInitialValues}
    fieldDisplay={fieldDisplay}
    {...props}
  />
})

ListFieldView.propTypes = {
  field: PropTypes.string.isRequired,
  initialValues: PropTypes.object,
  addElementLabel: PropTypes.string,
  formFieldProps: PropTypes.object,
  itemJoin: PropTypes.string,
  itemDisplay: PropTypes.func,
  itemKey: PropTypes.func,
}

export default ListFieldView
