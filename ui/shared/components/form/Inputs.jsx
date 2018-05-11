/* eslint-disable react/no-multi-comp */

import React, { createElement } from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Form } from 'semantic-ui-react'

class BaseSemanticInput extends React.Component {

  static propTypes = {
    onChange: PropTypes.func,
    inputType: PropTypes.string.isRequired,
  }

  handleChange = (e, data) => {
    this.props.onChange(data.value || data)
  }

  render() {
    const { inputType, ...props } = this.props
    return createElement(Form[inputType], { ...props, onChange: this.handleChange, onBlur: null })
  }
}

const labelStyle = (color) => { return color ? { color: 'white', backgroundColor: color } : {} }

const styledOption = (option) => {
  return {
    key: option.text || option.value,
    text: option.text || option.name || option.value,
    label: option.color ? { empty: true, circular: true, style: labelStyle(option.color) } : null,
    ...option,
  }
}

export const Select = props =>
  <BaseSemanticInput
    {...props}
    inputType="Select"
    options={props.options.map(styledOption)}
    fluid
    noResultsMessage={null}
    tabIndex="0"
  />


Select.propTypes = {
  options: PropTypes.array,
}

export class Multiselect extends React.Component {
  static propTypes = {
    color: PropTypes.string,
    options: PropTypes.array,
    onBlur: PropTypes.func,
    onChange: PropTypes.func,
  }

  state = {
    options: this.props.options,
  }

  renderLabel = (data) => {
    return { color: this.props.color, content: data.text || data.value, style: labelStyle(data.color) }
  }

  handleAddition = (e, option) => {
    this.setState({
      options: [option, ...this.state.options],
    })
  }

  render() {
    return <Select
      {...this.props}
      options={this.state.options}
      renderLabel={this.renderLabel}
      onAddItem={this.handleAddition}
      multiple
      search
    />
  }
}
export const StringValueCheckboxGroup = (props) => {
  const { value, options, onChange, ...baseProps } = props
  return (
    <Form.Group inline style={{ flexWrap: 'wrap' }}>
      {options.map(option =>
        <BaseSemanticInput
          {...baseProps}
          key={option.value}
          inputType="Checkbox"
          defaultChecked={value && value.includes(option.value)}
          label={option.name}
          onChange={({ checked }) => {
            let newValue
            if (checked) {
              newValue = value + option.value
            } else {
              newValue = value.replace(option.value, '')
            }
            onChange(newValue)
          }}
        />,
      )}
    </Form.Group>
  )
}

StringValueCheckboxGroup.propTypes = {
  value: PropTypes.string,
  options: PropTypes.array,
  onChange: PropTypes.func,
}

export const BooleanCheckbox = (props) => {
  const { value, ...baseProps } = props
  return <BaseSemanticInput
    {...baseProps}
    inputType="Checkbox"
    defaultChecked={Boolean(value)}
  />
}

BooleanCheckbox.propTypes = {
  value: PropTypes.any,
}

const StyledInlineToggle = styled(BooleanCheckbox)`
  .ui.toggle.checkbox label {
    font-size: small;
    padding-top: 0;
  }
  
  .ui.toggle.checkbox, .ui.toggle.checkbox input, .ui.toggle.checkbox label, .ui.toggle.checkbox label:before, .ui.toggle.checkbox label:after {
    height: 1.2em !important;
    min-height: 1.2em !important;
  }
  
  .ui.toggle.checkbox input:checked ~ label:before {
    background-color: ${props => `${props.color || '#2185D0'} !important`}
  }
`

export const InlineToggle = props => <StyledInlineToggle toggle inline {...props} />
