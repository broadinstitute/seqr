/* eslint-disable react/no-multi-comp */

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Form, Checkbox } from 'semantic-ui-react'

const labelStyle = (color) => { return color ? { color: 'white', backgroundColor: color } : {} }

const styledOption = (option) => {
  if (option.header) {
    // semantic-ui doesn't support optgroups in multiple dropdowns, so this is a workaround
    return { key: option.content, content: option.content, className: 'header', selected: false, onClick: () => {}, style: { cursor: 'auto', backgroundColor: 'initial' } }
  }
  return {
    key: option.value,
    text: option.text || option.value,
    label: option.color ? { empty: true, circular: true, style: labelStyle(option.color) } : null,
    ...option,
  }
}

export class Multiselect extends React.Component {
  static propTypes = {
    color: PropTypes.string,
    options: PropTypes.array,
    onBlur: PropTypes.func,
    onChange: PropTypes.func,
  }

  state = {
    options: this.props.options.map(styledOption),
  }

  renderLabel = (data) => {
    return { color: this.props.color, content: data.text || data.value, style: labelStyle(data.color) }
  }

  handleChange = (e, data) => {
    this.props.onChange(data.value)
  }

  handleAddition = (e, { value }) => {
    this.setState({
      options: [styledOption({ value }), ...this.state.options],
    })
  }

  render() {
    return <Form.Select
      {...this.props}
      options={this.state.options}
      renderLabel={this.renderLabel}
      onChange={this.handleChange}
      onBlur={null}
      onAddItem={this.handleAddition}
      fluid
      multiple
      search
      selection
      noResultsMessage={null}
      tabIndex="0"
    />
  }
}


const StyledInlineToggle = styled(Checkbox)`
  &.ui.toggle.checkbox label {
    font-size: small;
    padding-top: 0;
  }
  
  &.ui.toggle.checkbox, &.ui.toggle.checkbox input, &.ui.toggle.checkbox label, &.ui.toggle.checkbox label:before, &.ui.toggle.checkbox label:after {
    height: 1.2em !important;
    min-height: 1.2em !important;
  }
  
  &.ui.toggle.checkbox input:checked ~ label:before {
    background-color: ${props => `${props.color || '#2185D0'} !important`}
  }
`

export class InlineToggle extends React.Component {

  static propTypes = {
    onChange: PropTypes.func,
  }

  handleChange = (e, data) => {
    this.props.onChange(data)
  }

  render() {
    return <StyledInlineToggle
      toggle
      {...this.props}
      onChange={this.handleChange}
    />
  }
}
