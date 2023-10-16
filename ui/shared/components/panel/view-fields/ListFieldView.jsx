import React from 'react'
import PropTypes from 'prop-types'
import { Icon } from 'semantic-ui-react'

import BaseFieldView from './BaseFieldView'
import { BaseSemanticInput } from '../../form/Inputs'
import { validators } from '../../form/FormHelpers'
import { ButtonLink } from '../../StyledComponents'

const RemovableInput = React.memo(({ removeField, itemComponent, ...props }) => React.createElement(
  itemComponent || BaseSemanticInput, {
    icon: <Icon name="remove" link onClick={removeField} />,
    inputType: 'Input',
    ...props,
  },
))

RemovableInput.propTypes = {
  removeField: PropTypes.func,
  itemComponent: PropTypes.func,
}

const addElementNoDefault = addElement => (e) => {
  e.preventDefault()
  addElement()
}

const AddElementButton = React.memo(({ addElement, addElementLabel }) => (
  <ButtonLink
    icon="plus"
    content={addElementLabel}
    onClick={addElementNoDefault(addElement)}
  />
))

AddElementButton.propTypes = {
  addElementLabel: PropTypes.string,
  addElement: PropTypes.func,
}

class ListFieldView extends React.PureComponent {

  static propTypes = {
    field: PropTypes.string.isRequired,
    initialValues: PropTypes.object,
    addElementLabel: PropTypes.string,
    formFieldProps: PropTypes.object,
    itemJoin: PropTypes.string,
    itemDisplay: PropTypes.func,
    itemKey: PropTypes.func,
  }

  fieldDisplay = (values) => {
    const { itemJoin, itemDisplay, itemKey } = this.props
    return (itemJoin ? values.join(itemJoin) : values.filter(val => val).map(
      value => <div key={itemKey ? itemKey(value) : value}>{itemDisplay ? itemDisplay(value) : value}</div>,
    ))
  }

  defaultedInitialValues = () => {
    const { initialValues, field } = this.props
    const initialValue = initialValues[field]
    return (initialValue && initialValue.length) ? initialValues : {
      ...initialValues,
      [field]: [''],
    }
  }

  formFieldProps = () => {
    const { addElementLabel, formFieldProps = {} } = this.props
    return {
      isArrayField: true,
      addArrayElement: AddElementButton,
      addArrayElementProps: { addElementLabel },
      validate: validators.required,
      component: RemovableInput,
      ...formFieldProps,
    }
  }

  render() {
    const { addElementLabel, itemJoin, itemDisplay, itemKey, ...props } = this.props
    return (
      <BaseFieldView
        {...props}
        formFieldProps={this.formFieldProps()}
        initialValues={this.defaultedInitialValues()}
        fieldDisplay={this.fieldDisplay}
      />
    )
  }

}

export default ListFieldView
