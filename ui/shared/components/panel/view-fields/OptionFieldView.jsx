import React from 'react'
import PropTypes from 'prop-types'

import { Select } from '../../form/Inputs'
import BaseFieldView from './BaseFieldView'

class OptionFieldView extends React.PureComponent {

  static propTypes = {
    field: PropTypes.string.isRequired,
    initialValues: PropTypes.object.isRequired,
    tagOptions: PropTypes.arrayOf(PropTypes.object).isRequired,
    tagAnnotation: PropTypes.func,
    additionalEditFields: PropTypes.arrayOf(PropTypes.object),
    formFieldProps: PropTypes.object,
    fieldDisplay: PropTypes.func,
    compact: PropTypes.bool,
  }

  fieldDisplay = (value) => {
    const { tagAnnotation, compact, initialValues } = this.props
    const valueConfig = this.tagSelectOptions().find(option => option.value === value) || {}

    const annotation = tagAnnotation ? tagAnnotation(valueConfig, compact, initialValues) : null
    return (
      <span>
        {annotation}
        {compact && annotation ? '' : valueConfig.text }
      </span>
    )
  }

  formFieldProps = () => {
    const { formFieldProps = {} } = this.props
    return {
      options: this.tagSelectOptions(),
      includeCategories: true,
      component: Select,
      ...formFieldProps,
    }
  }

  tagSelectOptions = () => {
    const { tagOptions } = this.props
    return tagOptions.map(({ name, ...tag }) => ({ value: name, text: name, ...tag }))
  }

  render() {
    const { fieldDisplay, tagOptions, tagAnnotation, ...props } = this.props

    return (
      <BaseFieldView
        {...props}
        fieldDisplay={fieldDisplay || this.fieldDisplay}
        formFieldProps={this.formFieldProps()}
      />
    )
  }

}

export default OptionFieldView
