import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Form, Header, Icon, Popup, Message } from 'semantic-ui-react'

import {
  getProjectsByGuid,
  getFamiliesGroupedByProjectGuid,
  getAnalysisGroupsGroupedByProjectGuid,
  getFamiliesByGuid,
  getAnalysisGroupsByGuid,
} from 'redux/selectors'
import { Multiselect, BooleanCheckbox } from 'shared/components/form/Inputs'
import { configuredField } from 'shared/components/form/ReduxFormWrapper'
import AwesomeBar from 'shared/components/page/AwesomeBar'
import DataLoader from 'shared/components/DataLoader'
import { InlineHeader, ButtonLink } from 'shared/components/StyledComponents'
import { VerticalSpacer } from 'shared/components/Spacers'
import { getSelectedAnalysisGroups } from '../../constants'
import { getProjectFamilies, getSearchContextIsLoading, getFamilyOptions, getAnalysisGroupOptions } from '../../selectors'
import { loadProjectFamiliesContext, loadProjectGroupContext } from '../../reducers'


const ProjectFamiliesFilterInput = ({ familyOptions, analysisGroupOptions, projectAnalysisGroupsByGuid, value, onChange, ...props }) => {
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
}

ProjectFamiliesFilterInput.propTypes = {
  familyOptions: PropTypes.array,
  analysisGroupOptions: PropTypes.array,
  projectAnalysisGroupsByGuid: PropTypes.object,
  value: PropTypes.any,
  onChange: PropTypes.func,
}

const ProjectFamiliesFilterContent = ({ project, removeField, dispatch, ...props }) => (
  <div>
    <Header>
      <Popup
        trigger={<ButtonLink onClick={removeField}><Icon name="remove" color="grey" /></ButtonLink>}
        content="Remove this project from search"
      />
      Project: <Link to={`/project/${project.projectGuid}/project_page`}>{project.name}</Link>
    </Header>
    {project.hasNewSearch ? <ProjectFamiliesFilterInput {...props} /> :
    <Message
      color="red"
      header="This search is not enabled for this project"
      content={
        <div>
          Please contact the seqr team to add this functionality. You can access this project&apos;s Gene Search
          &nbsp;<a href={`/project/${project.deprecatedProjectId}/gene`}>here</a>
        </div>}
    />}
    <VerticalSpacer height={10} />
  </div>
)

ProjectFamiliesFilterContent.propTypes = {
  project: PropTypes.object,
  removeField: PropTypes.func,
  dispatch: PropTypes.func,
}

const LoadedProjectFamiliesFilter = ({ loading, load, ...props }) =>
  <DataLoader
    contentId={props.value}
    loading={loading}
    load={load}
    content={props.project}
    hideError
  >
    <ProjectFamiliesFilterContent {...props} />
  </DataLoader>

LoadedProjectFamiliesFilter.propTypes = {
  project: PropTypes.object,
  value: PropTypes.object,
  load: PropTypes.func,
  loading: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  familyOptions: getFamilyOptions(state, ownProps),
  analysisGroupOptions: getAnalysisGroupOptions(state, ownProps),
  projectAnalysisGroupsByGuid: getAnalysisGroupsGroupedByProjectGuid(state)[ownProps.value.projectGuid] || {},
  project: getProjectsByGuid(state)[ownProps.value.projectGuid],
  loading: getSearchContextIsLoading(state),
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

const ProjectFamiliesFilter = connect(mapStateToProps, mapDispatchToProps)(LoadedProjectFamiliesFilter)

const PROJECT_SEARCH_CATEGORIES = ['projects']
const PROJECT_GROUP_SEARCH_CATEGORIES = ['project_groups']

const BaseAddProjectButton = ({ addElement, addProjectGroup }) =>
  <div>
    <InlineHeader content="Add Project:" />
    <AwesomeBar
      categories={PROJECT_SEARCH_CATEGORIES}
      placeholder="Search for a project"
      inputwidth="400px"
      onResultSelect={result => addElement({ projectGuid: result.key })}
    />
    <InlineHeader content="Add Project Group:" />
    <AwesomeBar
      categories={PROJECT_GROUP_SEARCH_CATEGORIES}
      placeholder="Search for a project group"
      inputwidth="400px"
      onResultSelect={result => addProjectGroup(result.key, addElement)}
    />
  </div>

BaseAddProjectButton.propTypes = {
  addElement: PropTypes.func,
  addProjectGroup: PropTypes.func,
}

const mapAddProjectDispatchToProps = {
  addProjectGroup: loadProjectGroupContext,
}

const AddProjectButton = connect(null, mapAddProjectDispatchToProps)(BaseAddProjectButton)

const validateFamilies = value => (value && value.familyGuids && value.familyGuids.length ? undefined : 'Families are required for all projects')

const PROJECT_FAMILIES_FIELD = {
  name: 'projectFamilies',
  component: ProjectFamiliesFilter,
  addArrayElement: AddProjectButton,
  validate: validateFamilies,
  isArrayField: true,
}

export default () => configuredField(PROJECT_FAMILIES_FIELD)
