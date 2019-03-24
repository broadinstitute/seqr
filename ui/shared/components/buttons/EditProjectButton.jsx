import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'

import { updateProject } from 'redux/rootReducer'
import UpdateButton from '../buttons/UpdateButton'
import { EDITABLE_PROJECT_FIELDS } from '../../utils/constants'

const EditProjectButton = props => (
  props.project && props.project.canEdit ?
    <UpdateButton
      buttonText="Edit Project"
      modalTitle="Edit Project"
      modalId={`editProject-${props.project.projectGuid}`}
      onSubmit={props.updateProject}
      formFields={EDITABLE_PROJECT_FIELDS}
      initialValues={props.project}
      trigger={props.trigger}
      submitButtonText="Save"
    /> : null
)

EditProjectButton.propTypes = {
  project: PropTypes.object,
  updateProject: PropTypes.func,
  trigger: PropTypes.node,
}

const mapDispatchToProps = {
  updateProject,
}

export default connect(null, mapDispatchToProps)(EditProjectButton)
