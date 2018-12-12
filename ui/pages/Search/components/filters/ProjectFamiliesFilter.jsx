import React from 'react'
import PropTypes from 'prop-types'
import { formValueSelector } from 'redux-form'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Form, Header } from 'semantic-ui-react'

import { getProjectsByGuid, getFamiliesGroupedByProjectGuid } from 'redux/selectors'
import { Multiselect, BooleanCheckbox } from 'shared/components/form/Inputs'


const ProjectFamiliesFilter = ({ projectFamiliesByGuid, project, value, onChange, removeField, dispatch, ...props }) => {
  const familyOptions = Object.values(projectFamiliesByGuid).map(
    family => ({ value: family.familyGuid, text: family.displayName }),
  )
  const selectAllFamilies = (checked) => {
    if (checked) {
      onChange(familyOptions.map((opt => opt.value)))
    }
  }
  // TODO analysis groups
  return (
    <div>
      {project &&
        <Header>
          Project: <Link to={`/project/${project.projectGuid}/project_page`}>{project.name}</Link>
        </Header>
      }
      <Form.Group inline>
        <BooleanCheckbox
          {...props}
          value={value.length === familyOptions.length}
          onChange={selectAllFamilies}
          width={2}
          label="Include All Families"
        />
        <Multiselect
          {...props}
          value={value}
          onChange={onChange}
          width={7}
          options={familyOptions}
          label="Families"
        />
      </Form.Group>
    </div>
  )
}

const mapStateToProps = (state, ownProps) => {
  const projectGuid = formValueSelector(ownProps.meta.form)(state, ownProps.name.replace('familyGuids', 'projectGuid'))
  return ({
    projectFamiliesByGuid: getFamiliesGroupedByProjectGuid(state)[projectGuid] || {},
    project: getProjectsByGuid(state)[projectGuid],
  })
}

ProjectFamiliesFilter.propTypes = {
  name: PropTypes.string,
  project: PropTypes.object,
  projectFamiliesByGuid: PropTypes.object,
  value: PropTypes.array,
  onChange: PropTypes.func,
  removeField: PropTypes.func,
  dispatch: PropTypes.func,
}


export default connect(mapStateToProps)(ProjectFamiliesFilter)
