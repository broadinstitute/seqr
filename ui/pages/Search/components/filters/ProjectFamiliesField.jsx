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
import { configuredField } from 'shared/components/form/ReduxFormWrapper'
import { AddProjectButton, ProjectFilter } from 'shared/components/panel/search/ProjectsField'
import { ButtonLink } from 'shared/components/StyledComponents'
import { getSelectedAnalysisGroups } from '../../constants'
import { getProjectFamilies, getSearchContextIsLoading, getFamilyOptions, getAnalysisGroupOptions, getInputProjectsCount } from '../../selectors'
import { loadProjectFamiliesContext, loadProjectGroupContext } from '../../reducers'


const ProjectFamiliesFilterInput = React.memo(({ familyOptions, analysisGroupOptions, projectAnalysisGroupsByGuid, value, onChange, ...props }) => {
  const allFamiliesSelected = !value.familyGuids || value.familyGuids.length === familyOptions.length

  const selectedFamilies = allFamiliesSelected ? [] : value.familyGuids

  const onFamiliesChange = familyGuids => onChange({ ...value, familyGuids })

  const selectedAnalysisGroups = allFamiliesSelected ? [] :
    getSelectedAnalysisGroups(projectAnalysisGroupsByGuid, value.familyGuids).map(group => group.analysisGroupGuid)

  const selectAnalysisGroup = (analysisGroups) => {
    if (analysisGroups.length > selectedAnalysisGroups.length) {
      const newGroupGuid = analysisGroups.find(analysisGroupGuid => !selectedAnalysisGroups.includes(analysisGroupGuid))
      onFamiliesChange([...new Set([...value.familyGuids, ...projectAnalysisGroupsByGuid[newGroupGuid].familyGuids])])
    } else if (analysisGroups.length < selectedAnalysisGroups.length) {
      const removedGroupGuid = selectedAnalysisGroups.find(analysisGroupGuid => !analysisGroups.includes(analysisGroupGuid))
      onFamiliesChange(value.familyGuids.filter(familyGuid => !projectAnalysisGroupsByGuid[removedGroupGuid].familyGuids.includes(familyGuid)))
    }
  }

  const selectAllFamilies = (checked) => {
    if (checked) {
      onFamiliesChange(familyOptions.map((opt => opt.value)))
    } else {
      onFamiliesChange([])
    }
  }

  return (
    <Form.Group inline widths="equal">
      <BooleanCheckbox
        {...props}
        value={allFamiliesSelected}
        onChange={selectAllFamilies}
        width={5}
        label="Include All Families"
      />
      <Multiselect
        {...props}
        value={selectedFamilies}
        onChange={onFamiliesChange}
        options={familyOptions}
        disabled={allFamiliesSelected}
        label="Families"
        color="violet"
      />
      <Multiselect
        {...props}
        value={selectedAnalysisGroups}
        onChange={selectAnalysisGroup}
        options={analysisGroupOptions}
        disabled={allFamiliesSelected}
        label="Analysis Groups"
        color="pink"
      />
    </Form.Group>
  )
})

ProjectFamiliesFilterInput.propTypes = {
  familyOptions: PropTypes.array,
  analysisGroupOptions: PropTypes.array,
  projectAnalysisGroupsByGuid: PropTypes.object,
  value: PropTypes.any,
  onChange: PropTypes.func,
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

const ProjectFamiliesFilter = connect(mapStateToProps, mapDispatchToProps)(ProjectFilter)

const AddProjectFamiliesButton = props =>
  <AddProjectButton processAddedElement={result => ({ projectGuid: result.key })} {...props} />

const mapAddProjectDispatchToProps = {
  addProjectGroup: loadProjectGroupContext,
}

const validateFamilies = value => (value && value.familyGuids && value.familyGuids.length ? undefined : 'Families are required for all projects')

const PROJECT_FAMILIES_FIELD = {
  name: 'projectFamilies',
  component: ProjectFamiliesFilter,
  addArrayElement: connect(null, mapAddProjectDispatchToProps)(AddProjectFamiliesButton),
  validate: validateFamilies,
  isArrayField: true,
}

class AllProjectFamiliesField extends React.PureComponent {
  state = { viewAllProjects: false }

  viewProjects = (e) => {
    e.preventDefault()
    this.setState({ viewAllProjects: true })
  }

  render() {
    return this.props.numProjects < 20 || this.state.viewAllProjects ?
      configuredField(PROJECT_FAMILIES_FIELD) : <ButtonLink onClick={this.viewProjects} content={`Show all ${this.props.numProjects} searched projects`} />
  }
}

AllProjectFamiliesField.propTypes = {
  numProjects: PropTypes.number,
}

const mapAllProjectFamiliesFieldStateToProps = state => ({
  numProjects: getInputProjectsCount(state),
})

export default connect(mapAllProjectFamiliesFieldStateToProps)(AllProjectFamiliesField)
