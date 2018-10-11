import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'

import { updateProject } from 'redux/rootReducer'
import ReduxFormWrapper from '../form/ReduxFormWrapper'
import Modal from './Modal'
import { PROJECT_FIELDS, GENOME_VERSION_37 } from '../../utils/constants'

const PROJECT_FIELD_LOOKUP = PROJECT_FIELDS.reduce(
  (acc, field) => ({
    ...acc,
    ...{ [field.name]: [field] },
  }), {},
)

const DEFAULT_PROJECT = {
  genomeVersion: GENOME_VERSION_37,
}


const EditProjectModal = (props) => {
  const name = `editProject${props.field || ''}-${props.project ? props.project.projectGuid : 'create'}`
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
        initialValues={props.project || DEFAULT_PROJECT}
        fields={props.field ? PROJECT_FIELD_LOOKUP[props.field] : PROJECT_FIELDS}
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

