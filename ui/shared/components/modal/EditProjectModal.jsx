import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'

import { updateProject } from 'redux/rootReducer'
import ReduxFormWrapper, { validators } from '../form/ReduxFormWrapper'
import Modal from './Modal'


const EditProjectModal = props =>
  <Modal trigger={props.trigger} title={props.title || 'Edit Project'} >
    <ReduxFormWrapper
      onSubmit={props.updateProject}
      form="editProject"
      submitButtonText="Save"
      initialValues={{
        name: props.project && props.project.name,
        description: props.project && props.project.description,
        projectGuid: props.project && props.project.projectGuid,
      }}
      fields={[
        { name: 'name', label: 'Project Name', placeholder: 'Name', validate: validators.required, autoFocus: true },
        { name: 'description', label: 'Project Description', placeholder: 'Description' },
      ]}
    />
  </Modal>

EditProjectModal.propTypes = {
  trigger: PropTypes.node.isRequired,
  title: PropTypes.string,
  project: PropTypes.object,
  updateProject: PropTypes.func.isRequired,
}

const mapDispatchToProps = {
  updateProject,
}

export default connect(null, mapDispatchToProps)(EditProjectModal)

