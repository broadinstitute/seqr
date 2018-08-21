/* eslint-disable react/no-multi-comp */

import React, { createElement } from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Form } from 'semantic-ui-react'
import Slider from 'react-rangeslider'
import 'react-rangeslider/lib/index.css'

class BaseSemanticInput extends React.Component {

  static propTypes = {
    onChange: PropTypes.func,
    inputType: PropTypes.string.isRequired,
  }

  handleChange = (e, data) => {
    this.props.onChange(data.value === undefined ? data : data.value)
  }

  render() {
    const { inputType, ...props } = this.props
    return createElement(Form[inputType], { ...props, onChange: this.handleChange, onBlur: null })
  }
}

const labelStyle = (color) => { return color ? { color: 'white', backgroundColor: color } : {} }

const styledOption = (option) => {
  return {
    value: option.value,
    key: option.text || option.value,
    text: option.text || option.name || option.value,
    label: option.color ? { empty: true, circular: true, style: labelStyle(option.color) } : null,
    color: option.color,
    disabled: option.disabled,
    description: option.description,
  }
}

const processOptions = (options, includeCategories) => {
  let currCategory = null
  return options.reduce((acc, option) => {
    if (includeCategories && option.category !== currCategory) {
      currCategory = option.category
      if (option.category) {
        acc.push({ text: option.category, disabled: true })
      }
    }
    acc.push(option)
    return acc
  }, []).map(styledOption)
}

export const Dropdown = ({ options, includeCategories, ...props }) =>
  <BaseSemanticInput
    {...props}
    inputType="Dropdown"
    options={processOptions(options, includeCategories)}
    noResultsMessage={null}
    tabIndex="0"
  />


Dropdown.propTypes = {
  options: PropTypes.array,
  includeCategories: PropTypes.bool,
}

export const Select = props =>
  <Dropdown selection fluid {...props} />


Select.propTypes = {
  options: PropTypes.array,
}

export class Multiselect extends React.PureComponent {
  static propTypes = {
    color: PropTypes.string,
    options: PropTypes.array,
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

const InlineFormGroup = styled(Form.Group).attrs({ inline: true })`
  flex-wrap: wrap;
  margin: ${props => props.margin || '0em 0em 1em'} !important;
`

export const StringValueCheckboxGroup = (props) => {
  const { value = '', options, onChange, ...baseProps } = props
  return (
    <InlineFormGroup>
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
    </InlineFormGroup>
  )
}

StringValueCheckboxGroup.propTypes = {
  value: PropTypes.any,
  options: PropTypes.array,
  onChange: PropTypes.func,
}


export const RadioGroup = (props) => {
  const { value, options, label, onChange, margin, ...baseProps } = props
  return (
    <InlineFormGroup margin={margin}>
      {label}
      {options.map(option =>
        <BaseSemanticInput
          {...baseProps}
          key={option.value}
          inline
          inputType="Radio"
          checked={value === option.value}
          label={option.text}
          onChange={({ checked }) => {
            if (checked) {
              onChange(option.value)
            }
          }}
        />,
      )}
    </InlineFormGroup>
  )
}

RadioGroup.propTypes = {
  value: PropTypes.any,
  options: PropTypes.array,
  onChange: PropTypes.func,
  label: PropTypes.node,
  margin: PropTypes.string,
}

export const BooleanCheckbox = (props) => {
  const { value, onChange, ...baseProps } = props
  return <BaseSemanticInput
    {...baseProps}
    inputType="Checkbox"
    checked={Boolean(value)}
    onChange={data => onChange(data.checked)}
  />
}

BooleanCheckbox.propTypes = {
  value: PropTypes.any,
  onChange: PropTypes.func,
}

export const InlineToggle = styled(BooleanCheckbox).attrs({ toggle: true, inline: true })`
  padding-right: 10px;
  
  .ui.toggle.checkbox label {
    font-size: small;
    padding: 0 4.5em 0 0;
  }
  
  .ui.toggle.checkbox, .ui.toggle.checkbox input, .ui.toggle.checkbox label, .ui.toggle.checkbox label:before, .ui.toggle.checkbox label:after {
    left: auto !important;
    right: 0  !important;
    height: 1.2em !important;
    min-height: 1.2em !important;
  }
  
  .ui.toggle.checkbox input:checked ~ label:before {
    background-color: ${props => `${props.color || '#2185D0'} !important`};
    right: 0.1em !important;
  }
  
  .ui.toggle.checkbox input:not(:checked) ~ label:after {
    right: 2em !important;
  }
`

export const LabeledSlider = styled(Slider).attrs({
  handleLabel: props => `${props.valueLabel || props.value}`,
  labels: props => ({ [props.min]: props.minLabel || props.min, [props.max]: props.maxLabel || props.max }),
  tooltip: false,
})`
  .rangeslider__fill {
    background-color: grey !important;
  }

  .rangeslider__handle {
    .rangeslider__handle-label {
      text-align: center;
      margin-top: .35em;
      font-size: .9em;
    }
    
    &:after {
      display: none;
    }
  }
  
  .rangeslider__labels .rangeslider__label-item {
    top: -10px;
  }
`

export const StepSlider = ({ steps, stepLabels, value, onChange, ...props }) =>
  <LabeledSlider
    {...props}
    min={0}
    minLabel={stepLabels[steps[0]] || steps[0]}
    max={steps.length - 1}
    maxLabel={stepLabels[steps.length - 1] || steps[steps.length - 1]}
    value={steps.indexOf(value)}
    valueLabel={stepLabels[value] || value}
    onChange={val => onChange(steps[val])}
  />


StepSlider.propTypes = {
  value: PropTypes.any,
  steps: PropTypes.array,
  stepLabels: PropTypes.object,
  onChange: PropTypes.func,
}
