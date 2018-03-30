import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Dropdown, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { updateProject } from 'redux/rootReducer'
import { computeCaseReviewUrl } from 'shared/utils/urlUtils'
import Modal from 'shared/components/modal/Modal'
import ReduxFormWrapper, { validators } from 'shared/components/form/ReduxFormWrapper'
import EditProjectCategoriesModal from './EditProjectCategoriesModal'

const EllipsisContainer = styled.span`
  padding: 3px;

  &:hover {
    padding: 3px;
    background-color: #fafafa;
    border-color: #ccc;
    border-radius: 3px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
  }
`

const ProjectEllipsisMenu = props =>
  <EllipsisContainer>{
    <Dropdown pointing="top right" icon={
      <Icon name="ellipsis vertical" />}
    >
      <Dropdown.Menu>
        {props.user.is_staff && [
          <Dropdown.Item key={1} onClick={() => { window.open(computeCaseReviewUrl(props.project.projectGuid), '_blank') }}>
            Case Review Page
          </Dropdown.Item>,
          <Dropdown.Divider key={2} />,
        ]}

        {(props.user.is_staff || props.project.canEdit) && [
          <Modal key={1} trigger={<Dropdown.Item>Edit Name</Dropdown.Item>} title="Edit Project Name" modalName="editProjectName">
            <ReduxFormWrapper
              initialValues={{ name: props.project.name, projectGuid: props.project.projectGuid }}
              onSubmit={props.updateProject}
              form="editProjectName"
              fields={[
                { name: 'name', validate: validators.required, autoFocus: true },
              ]}
            />
          </Modal>,
          <Modal key={2} trigger={<Dropdown.Item>Edit Description</Dropdown.Item>} title="Edit Project Description" modalName="editProjectDescription">
            <ReduxFormWrapper
              initialValues={{ description: props.project.description, projectGuid: props.project.projectGuid }}
              onSubmit={props.updateProject}
              form="editProjectDescription"
              fields={[
                { name: 'description', autoFocus: true },
              ]}
            />
          </Modal>,
          <EditProjectCategoriesModal key={3} trigger={<Dropdown.Item>Edit Categories</Dropdown.Item>} project={props.project} />,

          <Dropdown.Divider key={4} />,

          <Dropdown.Item key={5} onClick={() => (window.open(`/project/${props.project.deprecatedProjectId}/collaborators`))}>
            Edit Collaborators
          </Dropdown.Item>,
          <Dropdown.Item key={6} onClick={() => (window.open(`/project/${props.project.deprecatedProjectId}/edit-individuals`))}>
            Edit Individuals
          </Dropdown.Item>,
          <Dropdown.Item key={7} onClick={() => (window.open(`/project/${props.project.deprecatedProjectId}/project_gene_list_settings`))}>
            Edit Gene Lists
          </Dropdown.Item>,
        ]}

        {props.user.is_staff && [
          <Dropdown.Divider key={1} />,
          <Modal key={2} trigger={<Dropdown.Item>Delete Project</Dropdown.Item>} title="Delete Project?" modalName="deleteProject">
            <ReduxFormWrapper
              initialValues={{ projectGuid: props.project.projectGuid, delete: true }}
              onSubmit={props.updateProject}
              form="deleteProject"
              submitButtonText="Yes"
            >
              <div style={{ textAlign: 'left' }}>Are you sure you want to delete project <b>{props.project.name}</b>?</div>
            </ReduxFormWrapper>
          </Modal>,
        ]}
      </Dropdown.Menu>
    </Dropdown>
  }
  </EllipsisContainer>


export { ProjectEllipsisMenu as ProjectEllipsisMenuComponent }


ProjectEllipsisMenu.propTypes = {
  user: PropTypes.object.isRequired,
  project: PropTypes.object.isRequired,
  updateProject: PropTypes.func.isRequired,
}

const mapStateToProps = state => ({ user: state.user })

const mapDispatchToProps = { updateProject }

export default connect(mapStateToProps, mapDispatchToProps)(ProjectEllipsisMenu)
