import React from 'react'
import PropTypes from 'prop-types'

import { Form } from 'semantic-ui-react'
import { connect } from 'react-redux'

import ModalWithForm from 'shared/components/modal/ModalWithForm'
import { updateProject } from 'shared/utils/commonReducers'

import { getEditProjectModalIsVisible, getEditProjectModalProject, hideEditProjectModal } from './state'


const EditProjectModal = props => (
  props.isVisible ?
    <ModalWithForm
      title={'Edit Project'}
      formSubmitUrl={`/api/project/${props.project.projectGuid}/update_project`}
      submitButtonText={'Save'}
      onValidate={(formData) => {
        if (!formData.name || !formData.name.trim()) {
          return { errors: { name: 'is empty' } }
        }
        return {}
      }}
      onSave={(responseJson) => {
        console.log('EditProjectModal - got response', responseJson.projectsByGuid[props.project.projectGuid])
        props.updateProject(responseJson.projectsByGuid[props.project.projectGuid])
      }}
      onClose={props.hideEditProjectModal}
      size="large"
      confirmCloseIfNotSaved={false}
    >
      <Form.Input key={1} label="Project Name" name="name" placeholder="Name" autoFocus defaultValue={props.project.name} />,
      <Form.Input key={2} label="Project Description" name="description" placeholder="Description" defaultValue={props.project.description} />
    </ModalWithForm> : null
)

EditProjectModal.propTypes = {
  isVisible: PropTypes.bool.isRequired,
  project: PropTypes.object,
  updateProject: PropTypes.func.isRequired,
  hideEditProjectModal: PropTypes.func.isRequired,
}

export { EditProjectModal as EditProjectModalComponent }

const mapStateToProps = state => ({
  isVisible: getEditProjectModalIsVisible(state),
  project: getEditProjectModalProject(state),
})

const mapDispatchToProps = {
  updateProject,
  hideEditProjectModal,
}

export default connect(mapStateToProps, mapDispatchToProps)(EditProjectModal)

