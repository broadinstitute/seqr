import React from 'react'
import PropTypes from 'prop-types'

import { Select } from '../../form/Inputs'
import BaseFieldView from './BaseFieldView'

class OptionFieldView extends React.PureComponent {

  static propTypes = {
    field: PropTypes.string.isRequired,
    initialValues: PropTypes.object.isRequired,
    tagOptions: PropTypes.arrayOf(PropTypes.object),
    tagAnnotation: PropTypes.func,
    tagOptionLookup: PropTypes.object,
    tagOptionLookupField: PropTypes.string,
    formatTagOption: PropTypes.func,
    additionalEditFields: PropTypes.arrayOf(PropTypes.object),
    formFieldProps: PropTypes.object,
    fieldDisplay: PropTypes.func,
    compact: PropTypes.bool,
    multiple: PropTypes.bool,
  }

  fieldDisplay = (value) => {
    const { multiple } = this.props
    return multiple ? value.map(v => <div key={v}>{this.singleFieldDisplay(v)}</div>) : this.singleFieldDisplay(value)
  }

  singleFieldDisplay = (value) => {
    const { tagAnnotation, compact, initialValues } = this.props
    const tagOptionLookup = this.tagOptionLookup()
    const valueConfig = (
      tagOptionLookup ? tagOptionLookup[value] : this.tagSelectOptions().find(option => option.value === value)) || {}

    const annotation = tagAnnotation ? tagAnnotation(valueConfig, compact, initialValues) : null
    return (
      <span>
        {annotation}
        {compact && annotation ? '' : (valueConfig.text || valueConfig.name) }
      </span>
    )
  }

  tagOptionLookup = () => {
    const { tagOptionLookupField, tagOptionLookup, initialValues } = this.props
    return tagOptionLookupField ? initialValues[tagOptionLookupField] : tagOptionLookup
  }

  formFieldProps = () => {
    const { multiple, formFieldProps = {} } = this.props
    return {
      options: this.tagSelectOptions(),
      includeCategories: true,
      component: Select,
      multiple,
      ...formFieldProps,
    }
  }

  tagSelectOptions = () => {
    const { tagOptions, formatTagOption } = this.props
    if (tagOptions) {
      return tagOptions.map(({ name, ...tag }) => ({ value: name, text: name, ...tag }))
    }
    return Object.values(this.tagOptionLookup()).map(formatTagOption)
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
