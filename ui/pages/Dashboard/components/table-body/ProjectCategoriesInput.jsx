import React from 'react'
import { Dropdown } from 'semantic-ui-react'
import { connect } from 'react-redux'
//import { bindActionCreators } from 'redux'
import { getProjectCategoriesByGuid } from '../../reducers/rootReducer'

class ProjectCategoriesInput extends React.Component {
  static propTypes = {
    project: React.PropTypes.object.isRequired,
    projectCategoriesByGuid: React.PropTypes.object.isRequired,
  }

  state = {
    currentCategories: this.props.project.projectCategoryGuids,
    existingCategories: Object.values(this.props.projectCategoriesByGuid).reduce((acc, projectCategory) => {
      acc[projectCategory.guid] = { value: projectCategory.guid, text: projectCategory.name }
      return acc
    }, {}),
  }

  handleAddition = (e, { value }) => {
    this.setState({
      existingCategories: { ...this.state.existingCategories, ...{ [value]: { value, text: value } } },
    })
  }

  handleChange = (e, { value }) => {
    this.setState({ currentCategories: value })
  }

  renderLabel = (data) => {
    return {
      color: 'blue',
      content: (this.props.projectCategoriesByGuid[data.value] && this.props.projectCategoriesByGuid[data.value].name) || data.value,
      //icon: 'check',
    }
  }

  /*
  onLabelClick = (e, { value }) => {
    console.log(e, value, 'clicked')
  }

  handleRef = (x) => {
    console.log('ref', x)
  }
  */

  render() {
    return <Dropdown
      //ref={this.handleRef}
      allowAdditions
      fluid
      multiple
      search
      selection
      noResultsMessage={null}
      additionLabel={'Category: '}
      name="categories"
      tabIndex="0"
      options={Object.values(this.state.existingCategories)}
      placeholder="Project categories"
      renderLabel={this.renderLabel}
      value={this.state.currentCategories}
      onAddItem={this.handleAddition}
      onChange={this.handleChange}
      //onLabelClick={this.onLabelClick}
    />
  }
}

export { ProjectCategoriesInput as ProjectCategoriesInputComponent }

const mapStateToProps = state => ({
  projectCategoriesByGuid: getProjectCategoriesByGuid(state),
})

const mapDispatchToProps = null //dispatch => bindActionCreators({ onChange: updateFilter }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(ProjectCategoriesInput)
