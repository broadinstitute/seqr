import React from 'react'
import PropTypes from 'prop-types'
import { Dropdown, Icon } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { computeCaseReviewUrl } from 'shared/utils/urlUtils'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import Modal from 'shared/components/modal/Modal'

import { EDIT_NAME_MODAL, EDIT_DESCRIPTION_MODAL, EDIT_CATEGORY_MODAL, DELETE_PROJECT_MODAL } from '../../constants'
import { showModal, saveProject } from '../../../../redux/rootReducer'


const ProjectEllipsisMenu = (props) => {
  const save = values => props.saveProject(Object.assign(values, { projectGuid: props.project.projectGuid }))

  return (
    <span className="ellipsis-menu">{
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
            <Modal key={1} trigger={<Dropdown.Item>Edit Name</Dropdown.Item>} title="Edit Project Name">
              <ReduxFormWrapper initialValues={{ name: props.project.name }} onSubmit={save} {...EDIT_NAME_MODAL} />
            </Modal>,
            <Modal key={2} trigger={<Dropdown.Item>Edit Description</Dropdown.Item>} title="Edit Project Description">
              <ReduxFormWrapper initialValues={{ description: props.project.description }} onSubmit={save} {...EDIT_DESCRIPTION_MODAL} />
            </Modal>,
            <Dropdown.Item key={3} onClick={() => { props.showModal(EDIT_CATEGORY_MODAL, props.project.projectGuid) }}>
              Edit Categories
            </Dropdown.Item>,

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
            <Dropdown.Item key={2} onClick={() => { props.showModal(DELETE_PROJECT_MODAL, props.project.projectGuid) }}>
              Delete Project
            </Dropdown.Item>,
          ]}
        </Dropdown.Menu>
      </Dropdown>
    }
    </span>
  )
}


export { ProjectEllipsisMenu as ProjectEllipsisMenuComponent }


ProjectEllipsisMenu.propTypes = {
  user: PropTypes.object.isRequired,
  project: PropTypes.object.isRequired,
  showModal: PropTypes.func.isRequired,
  saveProject: PropTypes.func.isRequired,
}

const mapStateToProps = state => ({ user: state.user })

const mapDispatchToProps = { showModal, saveProject }

export default connect(mapStateToProps, mapDispatchToProps)(ProjectEllipsisMenu)
