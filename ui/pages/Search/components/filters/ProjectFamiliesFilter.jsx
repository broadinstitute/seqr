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
import { getSelectedAnalysisGroups } from '../../constants'
import { getSearchedProjectsFamiliesInput } from '../../selectors'


const ProjectFamiliesFilter = (
  { projectFamiliesByGuid, projectAnalysisGroupsByGuid, project, value, onChange, removeField, dispatch, ...props },
) => {
  const familyOptions = Object.values(projectFamiliesByGuid).map(
    family => ({ value: family.familyGuid, text: family.displayName }),
  )

  const analysisGroupOptions = Object.values(projectAnalysisGroupsByGuid).map(
    group => ({ value: group.analysisGroupGuid, text: group.name }),
  )

  const selectedAnalysisGroups = getSelectedAnalysisGroups(projectAnalysisGroupsByGuid, value).map(
    group => group.analysisGroupGuid,
  )

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
          value={value.length === familyOptions.length}
          onChange={selectAllFamilies}
          width={5}
          label="Include All Families"
        />
        <Multiselect
          {...props}
          value={value}
          onChange={onChange}
          options={familyOptions}
          label="Families"
          color="violet"
        />
        <Multiselect
          {...props}
          value={selectedAnalysisGroups}
          onChange={selectAnalysisGroup}
          options={analysisGroupOptions}
          label="Analysis Groups"
          color="pink"
        />
      </Form.Group>
    </div>
  )
}

const mapStateToProps = (state, ownProps) => {
  const { projectGuid } = getSearchedProjectsFamiliesInput(state)[ownProps.index]
  return ({
    projectFamiliesByGuid: getFamiliesGroupedByProjectGuid(state)[projectGuid] || {},
    projectAnalysisGroupsByGuid: getAnalysisGroupsGroupedByProjectGuid(state)[projectGuid] || {},
    project: getProjectsByGuid(state)[projectGuid],
  })
}

ProjectFamiliesFilter.propTypes = {
  name: PropTypes.string,
  project: PropTypes.object,
  projectFamiliesByGuid: PropTypes.object,
  projectAnalysisGroupsByGuid: PropTypes.object,
  value: PropTypes.any,
  onChange: PropTypes.func,
  removeField: PropTypes.func,
  dispatch: PropTypes.func,
}


export default connect(mapStateToProps)(ProjectFamiliesFilter)
