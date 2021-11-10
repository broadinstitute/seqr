import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Form } from 'semantic-ui-react'

import {
  getProjectsByGuid,
  getFamiliesGroupedByProjectGuid,
  getAnalysisGroupsGroupedByProjectGuid,
  getFamiliesByGuid,
  getAnalysisGroupsByGuid,
  getSamplesGroupedByProjectGuid,
} from 'redux/selectors'
import { Multiselect, BooleanCheckbox } from 'shared/components/form/Inputs'
import { ProjectFilter } from 'shared/components/panel/search/ProjectsField'
import { getSelectedAnalysisGroups } from '../../constants'
import { getProjectFamilies, getSearchContextIsLoading, getFamilyOptions, getAnalysisGroupOptions } from '../../selectors'
import { loadProjectFamiliesContext } from '../../reducers'

class ProjectFamiliesFilterInput extends React.PureComponent {

  static propTypes = {
    familyOptions: PropTypes.arrayOf(PropTypes.object),
    analysisGroupOptions: PropTypes.arrayOf(PropTypes.object),
    projectAnalysisGroupsByGuid: PropTypes.object,
    value: PropTypes.object,
    onChange: PropTypes.func,
  }

  allFamiliesSelected = () => {
    const { familyOptions, value } = this.props
    return !value.familyGuids || value.familyGuids.length === familyOptions.length
  }

  selectedAnalysisGroups = () => {
    const { projectAnalysisGroupsByGuid, value } = this.props

    return this.allFamiliesSelected() ? [] :
      getSelectedAnalysisGroups(projectAnalysisGroupsByGuid, value.familyGuids).map(group => group.analysisGroupGuid)
  }

  onFamiliesChange = (familyGuids) => {
    const { value, onChange } = this.props
    onChange({ ...value, familyGuids })
  }

  selectAnalysisGroup = (analysisGroups) => {
    const { projectAnalysisGroupsByGuid, value } = this.props

    const selectedAnalysisGroups = this.selectedAnalysisGroups()

    if (analysisGroups.length > selectedAnalysisGroups.length) {
      const newGroupGuid = analysisGroups.find(analysisGroupGuid => !selectedAnalysisGroups.includes(analysisGroupGuid))
      this.onFamiliesChange(
        [...new Set([...value.familyGuids, ...projectAnalysisGroupsByGuid[newGroupGuid].familyGuids])],
      )
    } else if (analysisGroups.length < selectedAnalysisGroups.length) {
      const removedGroupGuid = selectedAnalysisGroups.find(
        analysisGroupGuid => !analysisGroups.includes(analysisGroupGuid),
      )
      this.onFamiliesChange(value.familyGuids.filter(
        familyGuid => !projectAnalysisGroupsByGuid[removedGroupGuid].familyGuids.includes(familyGuid),
      ))
    }
  }

  selectAllFamilies = (checked) => {
    const { familyOptions } = this.props
    if (checked) {
      this.onFamiliesChange(familyOptions.map((opt => opt.value)))
    } else {
      this.onFamiliesChange([])
    }
  }

  render() {
    const { familyOptions, analysisGroupOptions, projectAnalysisGroupsByGuid, value, onChange, ...props } = this.props
    const allFamiliesSelected = this.allFamiliesSelected()
    const selectedFamilies = allFamiliesSelected ? [] : value.familyGuids

    return (
      <Form.Group inline widths="equal">
        <BooleanCheckbox
          {...props}
          value={allFamiliesSelected}
          onChange={this.selectAllFamilies}
          width={5}
          label="Include All Families"
        />
        <Multiselect
          {...props}
          value={selectedFamilies}
          onChange={this.onFamiliesChange}
          options={familyOptions}
          disabled={allFamiliesSelected}
          label="Families"
          color="violet"
        />
        <Multiselect
          {...props}
          value={this.selectedAnalysisGroups()}
          onChange={this.selectAnalysisGroup}
          options={analysisGroupOptions}
          disabled={allFamiliesSelected}
          label="Analysis Groups"
          color="pink"
        />
      </Form.Group>
    )
  }

}

const mapStateToProps = (state, ownProps) => ({
  familyOptions: getFamilyOptions(state, ownProps),
  analysisGroupOptions: getAnalysisGroupOptions(state, ownProps),
  projectAnalysisGroupsByGuid: getAnalysisGroupsGroupedByProjectGuid(state)[ownProps.value.projectGuid] || {},
  project: getProjectsByGuid(state)[ownProps.value.projectGuid],
  projectSamples: getSamplesGroupedByProjectGuid(state)[ownProps.value.projectGuid],
  loading: getSearchContextIsLoading(state),
  filterInputComponent: ProjectFamiliesFilterInput,
})

const mapDispatchToProps = (dispatch, ownProps) => {
  const onLoadSuccess = (state) => {
    const newVal = getProjectFamilies(
      ownProps.value, getFamiliesByGuid(state), getFamiliesGroupedByProjectGuid(state), getAnalysisGroupsByGuid(state),
    )
    if (newVal && newVal !== ownProps.value) {
      ownProps.onChange(newVal)
    }
  }

  return {
    load: (context) => {
      dispatch(loadProjectFamiliesContext(context, onLoadSuccess))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(ProjectFilter)
