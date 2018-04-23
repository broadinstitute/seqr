/* eslint-disable react/no-multi-comp */

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Form, Checkbox } from 'semantic-ui-react'

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
    return { color: this.props.color, content: data.text || data.value }
  }

  handleChange = (e, data) => {
    this.props.onChange(data.value)
  }

  handleAddition = (e, { value }) => {
    this.setState({
      options: [{ text: value, value }, ...this.state.options],
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
      allowAdditions
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
