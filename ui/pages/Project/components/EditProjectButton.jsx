import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'

import { showEditProjectModal } from 'shared/components/modal/edit-project-modal/state'
import { getProject } from 'shared/utils/commonReducers'


const EditProjectButton = (props) => {
  return <a
    style={{ cursor: 'pointer' }}
    tabIndex="0"
    onClick={() => props.showEditProjectModal(props.project)}
  >
    Edit
  </a>
}

export { EditProjectButton as EditProjectButtonComponent }

EditProjectButton.propTypes = {
  project: PropTypes.object.isRequired,
  showEditProjectModal: PropTypes.func.isRequired,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

const mapDispatchToProps = {
  showEditProjectModal,
}

export default connect(mapStateToProps, mapDispatchToProps)(EditProjectButton)

