import React from 'react'
import PropTypes from 'prop-types'
import { Icon } from 'semantic-ui-react'

import BaseFieldView from './BaseFieldView'
import { BaseSemanticInput } from '../../form/Inputs'
import { validators } from '../../form/ReduxFormWrapper'
import { ButtonLink } from '../../StyledComponents'

const RemovableInput = React.memo(({ removeField, ...props }) =>
  <BaseSemanticInput icon={<Icon name="remove" link onClick={removeField} />} inputType="Input" {...props} />,
)

RemovableInput.propTypes = {
  removeField: PropTypes.func,
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

const ListFieldView = React.memo(({ addElementLabel, initialValues, formFieldProps = {}, ...props }) => {
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

  return <BaseFieldView
    formFields={fields}
    initialValues={defaultedInitialValues}
    {...props}
  />
})

ListFieldView.propTypes = {
  field: PropTypes.string.isRequired,
  initialValues: PropTypes.object,
  addElementLabel: PropTypes.string,
  formFieldProps: PropTypes.object,
}

export default ListFieldView
