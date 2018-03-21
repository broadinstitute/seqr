import React from 'react'
import PropTypes from 'prop-types'
import { Form } from 'semantic-ui-react'

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
