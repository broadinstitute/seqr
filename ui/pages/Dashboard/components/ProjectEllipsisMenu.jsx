import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Dropdown, Icon, Loader, Dimmer } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'

import { updateProject } from 'redux/rootReducer'
import { getUser, getProjectDetailsIsLoading } from 'redux/selectors'
import { loadProjectDetails } from 'redux/utils/reducerUtils'
import DeleteButton from 'shared/components/buttons/DeleteButton'
import EditProjectButton from 'shared/components/buttons/EditProjectButton'
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

const ProjectEllipsisMenu = React.memo((props) => {
  const menuItems = [
    props.loading ? <Dropdown.Item><Dimmer inverted active><Loader size="tiny" /></Dimmer></Dropdown.Item> : (
      <EditProjectButton
        key="edit"
        trigger={<Dropdown.Item>Edit Project</Dropdown.Item>}
        project={props.project}
        user={props.user}
      />
    ),
    <EditProjectCategoriesModal
      key="editCategories"
      trigger={<Dropdown.Item>Edit Categories</Dropdown.Item>}
      triggerName="ellipsesMenu"
      project={props.project}
    />,
  ]

  if (props.project.hasCaseReview) {
    menuItems.unshift(
      <Dropdown.Item
        key="caseReview"
        as={NavLink}
        to={`/project/${props.project.projectGuid}/case_review`}
        target="_blank"
      >
        Case Review Page
      </Dropdown.Item>,
      <Dropdown.Divider key="divider1" />,
    )
  }
  if (props.project.userCanDelete) {
    menuItems.push(
      <Dropdown.Divider key="divider2" />,
      <DeleteButton
        key="delete"
        buttonContainer={<Dropdown.Item />}
        buttonText="Delete Project"
        color="black"
        initialValues={props.project}
        onSubmit={props.updateProject}
        confirmDialog={`Are you sure you want to delete project "${props.project.name}"?`}
      />,
    )
  }

  return (
    <EllipsisContainer>
      <Dropdown pointing="top right" icon={<Icon name="ellipsis vertical" />} onOpen={props.load}>
        <Dropdown.Menu>{menuItems}</Dropdown.Menu>
      </Dropdown>
    </EllipsisContainer>
  )
})

export { ProjectEllipsisMenu as ProjectEllipsisMenuComponent }

ProjectEllipsisMenu.propTypes = {
  project: PropTypes.object.isRequired,
  user: PropTypes.object.isRequired,
  updateProject: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  load: PropTypes.func.isRequired,
}

const mapStateToProps = state => ({
  user: getUser(state),
  loading: getProjectDetailsIsLoading(state),
})

const mapDispatchToProps = (dispatch, ownProps) => ({
  load: () => {
    dispatch(loadProjectDetails(ownProps.project.projectGuid))
  },
  updateProject: (values) => {
    dispatch(updateProject(values))
  },
})

export default connect(mapStateToProps, mapDispatchToProps)(ProjectEllipsisMenu)
