import React from 'react'
import { Dropdown, Icon } from 'semantic-ui-react'

import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import { showModal } from '../reducers/modalDialogReducer'
import { computeCaseReviewUrl } from '../utils'
import { EDIT_NAME_MODAL, EDIT_DESCRIPTION_MODAL, EDIT_CATEGORY_MODAL } from '../constants'

const EllipsisMenu = props =>
  <span>{
    (props.user.is_staff || props.projectsByGuid[props.projectGuid].canEdit) &&
    <Dropdown pointing="top right" icon={
      <Icon style={{ paddingLeft: '10px', paddingRight: '15px' }} name="ellipsis vertical" />}
    >
      <Dropdown.Menu>
        <Dropdown.Item onClick={() => { props.showModal(EDIT_NAME_MODAL, props.projectGuid) }}>
          Edit Name
        </Dropdown.Item>
        <Dropdown.Item onClick={() => { props.showModal(EDIT_DESCRIPTION_MODAL, props.projectGuid) }}>
          Edit Description
        </Dropdown.Item>
        <Dropdown.Item onClick={() => { props.showModal(EDIT_CATEGORY_MODAL, props.projectGuid) }}>
          Edit Category
        </Dropdown.Item>
        <Dropdown.Divider />
        <Dropdown.Item onClick={() => (window.open(`/project/${props.projectsByGuid[props.projectGuid].deprecatedProjectId}/collaborators`))}>
          Edit Collaborators
        </Dropdown.Item>
        {props.user.is_staff && [
          <Dropdown.Divider key={1} />,
          <Dropdown.Item key={2} onClick={() => { window.open(computeCaseReviewUrl(props.projectGuid), '_blank') }}>
            Case Review
          </Dropdown.Item>,
        ]}
      </Dropdown.Menu>
    </Dropdown>
  }
  </span>

EllipsisMenu.propTypes = {
  user: React.PropTypes.object.isRequired,
  projectGuid: React.PropTypes.string.isRequired,
  projectsByGuid: React.PropTypes.object.isRequired,
}


const mapStateToProps = state => ({ user: state.user, projectsByGuid: state.projectsByGuid })

const mapDispatchToProps = dispatch => bindActionCreators({ showModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(EllipsisMenu)

