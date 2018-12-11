import React from 'react'
import PropTypes from 'prop-types'
import { formValueSelector } from 'redux-form'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Form, Header } from 'semantic-ui-react'

import { getProjectsByGuid, getFamiliesGroupedByProjectGuid } from 'redux/selectors'
import { Multiselect } from 'shared/components/form/Inputs'


const ProjectFamiliesFilter = ({ projectFamiliesByGuid, project, removeField, dispatch, ...props }) => {
  const familyOptions = Object.values(projectFamiliesByGuid).map(
    family => ({ value: family.familyGuid, text: family.displayName }),
  )
  // TODO handle multiple families
  return (
    <div>
      {project &&
        <Header>
          Project: <Link to={`/project/${project.projectGuid}/project_page`}>{project.name}</Link>
        </Header>
      }
      <Form.Group>
        <Multiselect
          {...props}
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
  removeField: PropTypes.func,
  dispatch: PropTypes.func,
}


export default connect(mapStateToProps)(ProjectFamiliesFilter)
