import React from 'react'
import { Dropdown } from 'semantic-ui-react'


const renderLabel = data => ({
  color: 'red',
  content: `${data.text}`,
  icon: 'check',
})


class DropdownWithAutoFocus extends Dropdown {
  constructor() {
    super()
    console.log('DropdownWithAutoFocus constructor')
  }

  renderSearchInput() {
    const cloned = React.cloneElement(super.renderSearchInput(), { autoFocus: 'autoFocus' })
    console.log('cloned', cloned)
    return cloned
  }
}


class ProjectCategoriesInput extends React.Component {
  state = {
    currentValue: [],
    categories: [],
  }
  //{ key: 1, text: 'One', value: 1 },

  handleAddition = (e, { value }) => {
    console.log('adding', value)
    this.setState({
      categories: [{ text: value, value }, ...this.state.categories],
    })
  }

  handleChange = (e, { value }) => {
    console.log('change', value)
    this.setState({ currentValue: value })
  }

  onLabelClick = (e, { value }) => {
    console.log('on label click', value)
  }

  handleRef = (x) => {
    console.log('ref', x)
  }

  render() {
    return <DropdownWithAutoFocus
      ref={this.handleRef}
      allowAdditions
      fluid
      multiple
      search
      selection
      noResultsMessage={null}
      additionLabel={'Category: '}
      name="ProjectCategories"
      tabIndex="0"
      options={this.state.categories}
      placeholder="Project categories"
      renderLabel={renderLabel}
      value={this.state.currentValue}
      onAddItem={this.handleAddition}
      onChange={this.handleChange}
    />
  }
}

export default ProjectCategoriesInput
