import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Dropdown, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'

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

const ProjectEllipsisMenu = (props) => {
  if (!props.user.isStaff && !props.project.canEdit) {
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

  if (props.user.isStaff) {
    menuItems.unshift(
      <Dropdown.Item key="caseReview" onClick={() => { window.open(`/project/${props.project.projectGuid}/case_review`, '_blank') }}>
        Case Review Page
      </Dropdown.Item>,
      <Dropdown.Divider key="divider1" />,
    )
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
}


export { ProjectEllipsisMenu as ProjectEllipsisMenuComponent }


ProjectEllipsisMenu.propTypes = {
  user: PropTypes.object.isRequired,
  project: PropTypes.object.isRequired,
  updateProject: PropTypes.func.isRequired,
}

const mapStateToProps = state => ({ user: state.user })

const mapDispatchToProps = { updateProject }

export default connect(mapStateToProps, mapDispatchToProps)(ProjectEllipsisMenu)
