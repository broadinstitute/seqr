import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'

import { updateProject } from 'redux/rootReducer'
import ReduxFormWrapper, { validators } from '../form/ReduxFormWrapper'
import Modal from './Modal'


const EditProjectModal = (props) => {
  const name = `editProject${props.field || ''}-${props.project ? props.project.projectGuid : 'create'}`
  let fields = [
    { name: 'name', label: 'Project Name', placeholder: 'Name', validate: validators.required, autoFocus: true },
    { name: 'description', label: 'Project Description', placeholder: 'Description' },
  ]
  if (props.field) {
    fields = fields.filter(field => field.name === props.field)
  }
  const initialValues = {
    name: props.project && props.project.name,
    description: props.project && props.project.description,
    projectGuid: props.project && props.project.projectGuid,
  }
  return (
    <Modal
      trigger={props.trigger}
      title={props.title || `Edit Project${props.field ? ` ${props.field[0].toUpperCase()}${props.field.slice(1)}` : ''}`}
      modalName={name}
    >
      <ReduxFormWrapper
        onSubmit={props.updateProject}
        form={name}
        submitButtonText="Save"
        initialValues={initialValues}
        fields={fields}
      />
    </Modal>
  )
}

EditProjectModal.propTypes = {
  trigger: PropTypes.node.isRequired,
  title: PropTypes.string,
  project: PropTypes.object,
  field: PropTypes.string,
  updateProject: PropTypes.func.isRequired,
}

const mapDispatchToProps = {
  updateProject,
}

export default connect(null, mapDispatchToProps)(EditProjectModal)

