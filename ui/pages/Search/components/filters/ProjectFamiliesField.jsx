import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Form, Header } from 'semantic-ui-react'

import {
  getProjectsByGuid,
  getFamiliesGroupedByProjectGuid,
  getAnalysisGroupsGroupedByProjectGuid,
} from 'redux/selectors'
import { Multiselect, BooleanCheckbox } from 'shared/components/form/Inputs'
import { configuredField } from 'shared/components/form/ReduxFormWrapper'
import AwesomeBar from 'shared/components/page/AwesomeBar'
import { InlineHeader } from 'shared/components/StyledComponents'
import { getSelectedAnalysisGroups } from '../../constants'
import { getProjectsFamiliesFieldInput } from '../../selectors'


const BaseProjectFamiliesFilter = (
  { projectFamiliesByGuid, projectAnalysisGroupsByGuid, project, value, onChange, removeField, dispatch, ...props },
) => {
  const familyOptions = Object.values(projectFamiliesByGuid).map(
    family => ({ value: family.familyGuid, text: family.displayName }),
  )

  const allFamiliesSelected = value.length === familyOptions.length

  const selectedFamilies = allFamiliesSelected ? [] : value

  const analysisGroupOptions = Object.values(projectAnalysisGroupsByGuid).map(
    group => ({ value: group.analysisGroupGuid, text: group.name }),
  )

  const selectedAnalysisGroups = allFamiliesSelected ? [] :
    getSelectedAnalysisGroups(projectAnalysisGroupsByGuid, value).map(group => group.analysisGroupGuid)

  const selectAnalysisGroup = (analysisGroups) => {
    if (analysisGroups.length > selectedAnalysisGroups.length) {
      const newGroupGuid = analysisGroups.find(analysisGroupGuid => !selectedAnalysisGroups.includes(analysisGroupGuid))
      onChange([...new Set([...value, ...projectAnalysisGroupsByGuid[newGroupGuid].familyGuids])])
    } else if (analysisGroups.length < selectedAnalysisGroups.length) {
      const removedGroupGuid = selectedAnalysisGroups.find(analysisGroupGuid => !analysisGroups.includes(analysisGroupGuid))
      onChange(value.filter(familyGuid => !projectAnalysisGroupsByGuid[removedGroupGuid].familyGuids.includes(familyGuid)))
    }
  }

  const selectAllFamilies = (checked) => {
    if (checked) {
      onChange(familyOptions.map((opt => opt.value)))
    } else {
      onChange([])
    }
  }

  return (
    <div>
      {project &&
        <Header>
          Project: <Link to={`/project/${project.projectGuid}/project_page`}>{project.name}</Link>
        </Header>
      }
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
          onChange={onChange}
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
    </div>
  )
}

BaseProjectFamiliesFilter.propTypes = {
  name: PropTypes.string,
  project: PropTypes.object,
  projectFamiliesByGuid: PropTypes.object,
  projectAnalysisGroupsByGuid: PropTypes.object,
  value: PropTypes.any,
  onChange: PropTypes.func,
  removeField: PropTypes.func,
  dispatch: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => {
  const { projectGuid } = getProjectsFamiliesFieldInput(state)[ownProps.index]
  return ({
    projectFamiliesByGuid: getFamiliesGroupedByProjectGuid(state)[projectGuid] || {},
    projectAnalysisGroupsByGuid: getAnalysisGroupsGroupedByProjectGuid(state)[projectGuid] || {},
    project: getProjectsByGuid(state)[projectGuid],
  })
}

const ProjectFamiliesFilter = connect(mapStateToProps)(BaseProjectFamiliesFilter)

const PROJECT_SEARCH_CATEGORIES = ['projects']

const AddProjectButton = ({ addElement }) =>
  <div>
    <InlineHeader content="Add Project:" />
    <AwesomeBar
      categories={PROJECT_SEARCH_CATEGORIES}
      placeholder="Search for a project"
      inputwidth="400px"
      onResultSelect={result => addElement({ projectGuid: result.key, familyGuids: [] })}
    />
  </div>

AddProjectButton.propTypes = {
  addElement: PropTypes.func,
}

const validateFamilies = value => (value && value.length ? undefined : 'Required')

const PROJECT_FAMILIES_FIELD = {
  name: 'projectFamilies',
  arrayFieldName: 'familyGuids',
  component: ProjectFamiliesFilter,
  addArrayElement: AddProjectButton,
  validate: validateFamilies,
  isArrayField: true,
}

export default () => configuredField(PROJECT_FAMILIES_FIELD)
