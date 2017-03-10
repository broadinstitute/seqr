import React from 'react'
import { Dropdown, Icon } from 'semantic-ui-react'

import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import { showModal } from '../../reducers/rootReducer'
import { computeCaseReviewUrl } from '../../utils/urlUtils'
import { EDIT_NAME_MODAL, EDIT_DESCRIPTION_MODAL, EDIT_CATEGORY_MODAL, DELETE_PROJECT_MODAL } from '../../constants'

const EllipsisMenu = props =>
  <span>{
    (props.user.is_staff || props.project.canEdit) &&
    <Dropdown pointing="top right" icon={
      <Icon name="ellipsis vertical" className="ProjectEllipsisMenu" />}
    >
      <Dropdown.Menu>
        <Dropdown.Item onClick={() => { window.open(`/project/${props.project.deprecatedProjectId}`, '_blank') }}>
            Project Page
        </Dropdown.Item>
        {props.user.is_staff && [
          <Dropdown.Item key={1} onClick={() => { window.open(computeCaseReviewUrl(props.project.projectGuid), '_blank') }}>
            Case Review Page
          </Dropdown.Item>,
          <Dropdown.Divider key={2} />,
        ]}

        <Dropdown.Item onClick={() => { props.showModal(EDIT_NAME_MODAL, props.project.projectGuid) }}>
          Edit Name
        </Dropdown.Item>
        <Dropdown.Item onClick={() => { props.showModal(EDIT_DESCRIPTION_MODAL, props.project.projectGuid) }}>
          Edit Description
        </Dropdown.Item>
        <Dropdown.Item onClick={() => { props.showModal(EDIT_CATEGORY_MODAL, props.project.projectGuid) }}>
          Edit Categories
        </Dropdown.Item>

        <Dropdown.Divider />

        <Dropdown.Item onClick={() => (window.open(`/project/${props.project.deprecatedProjectId}/collaborators`))}>
          Edit Collaborators
        </Dropdown.Item>
        <Dropdown.Item onClick={() => (window.open(`/project/${props.project.deprecatedProjectId}/edit-individuals`))}>
          Edit Individuals
        </Dropdown.Item>
        <Dropdown.Item onClick={() => (window.open(`/project/${props.project.deprecatedProjectId}/project_gene_list_settings`))}>
          Edit Gene Lists
        </Dropdown.Item>

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

EllipsisMenu.propTypes = {
  user: React.PropTypes.object.isRequired,
  project: React.PropTypes.object.isRequired,
  showModal: React.PropTypes.func.isRequired,
}


const mapStateToProps = state => ({ user: state.user })

const mapDispatchToProps = dispatch => bindActionCreators({ showModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(EllipsisMenu)

