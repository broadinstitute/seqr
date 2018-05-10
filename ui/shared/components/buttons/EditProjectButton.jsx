import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'

import { getProject } from 'pages/Project/selectors'
import EditProjectModal from '../modal/EditProjectModal'


const EditProjectButton = (props) => {
  if (props.project && props.project.canEdit) {
    return (
      <EditProjectModal
        trigger={<a tabIndex="0" role="button" style={{ cursor: 'pointer' }}>Edit</a>}
        project={props.project}
      />
    )
  }
  return null
}

export { EditProjectButton as EditProjectButtonComponent }

EditProjectButton.propTypes = {
  project: PropTypes.object,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(EditProjectButton)

