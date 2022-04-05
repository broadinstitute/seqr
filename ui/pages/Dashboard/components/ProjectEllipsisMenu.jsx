import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Dropdown, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'

import { updateProject } from 'redux/rootReducer'
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
  if (!props.project.canEdit) {
    return null
  }

  const menuItems = [
    <EditProjectButton
      key="edit"
      trigger={<Dropdown.Item>Edit Project</Dropdown.Item>}
      project={props.project}
    />,
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
  if (props.project.userIsCreator) {
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
      <Dropdown pointing="top right" icon={<Icon name="ellipsis vertical" />}>
        <Dropdown.Menu>{menuItems}</Dropdown.Menu>
      </Dropdown>
    </EllipsisContainer>
  )
})

export { ProjectEllipsisMenu as ProjectEllipsisMenuComponent }

ProjectEllipsisMenu.propTypes = {
  project: PropTypes.object.isRequired,
  updateProject: PropTypes.func.isRequired,
}

const mapDispatchToProps = { updateProject }

export default connect(null, mapDispatchToProps)(ProjectEllipsisMenu)
