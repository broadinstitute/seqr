import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import { Form } from 'semantic-ui-react'

import ModalWithForm from '../../../shared/components/ModalWithForm'

import { EDIT_NAME_MODAL, EDIT_DESCRIPTION_MODAL, ADD_PROJECT_MODAL, DELETE_PROJECT_MODAL } from '../constants'
import { hideModal, updateProjectsByGuid } from '../reducers/rootReducer'

class AddOrEditProjectModal extends React.PureComponent
{
  static propTypes = {
    modalDialogState: React.PropTypes.object.isRequired,
    project: React.PropTypes.object,
    hideModal: React.PropTypes.func.isRequired,
    updateProjectsByGuid: React.PropTypes.func.isRequired,
  }

  render() {
    if (!this.props.modalDialogState || !this.props.modalDialogState.modalIsVisible) {
      return null
    }

    let title = null
    let formFields = null
    let validation = null
    let url = null
    let submitButtonText = null
    switch (this.props.modalDialogState.modalType) {
      case EDIT_NAME_MODAL:
        title = 'Project Name'
        formFields = <Form.Input name={'name'} defaultValue={this.props.project.name} autoFocus />
        validation = this.handleValidation
        url = `/api/project/${this.props.project.projectGuid}/update_project`
        break
      case EDIT_DESCRIPTION_MODAL:
        title = 'Project Description'
        formFields = <Form.Input name={'description'} defaultValue={this.props.project.description} autoFocus />
        url = `/api/project/${this.props.project.projectGuid}/update_project`
        break
      case ADD_PROJECT_MODAL:
        title = 'Create Project'
        formFields = [
          <Form.Input label="Project Name" name="name" placeholder="Name" autoFocus />,
          <Form.Input label="Project Description" name="description" placeholder="Description" />,
        ]
        validation = this.handleValidation
        url = '/api/project/create_project'
        break
      case DELETE_PROJECT_MODAL:
        if (!this.props.project) {
          return null  // prevent null exception during the extra render after a project is deleted
        }
        title = 'Delete Project?'
        formFields = <div style={{ textAlign: 'left' }}>
          Are you sure you want to delete project <b>{this.props.project.name}</b>?
        </div>
        url = `/api/project/${this.props.project.projectGuid}/delete_project`
        submitButtonText = 'Yes'
        break
      default:
        return null
    }

    return <ModalWithForm
      title={title}
      submitButtonText={submitButtonText}
      onValidate={validation}
      onSave={(responseJson) => {
        this.props.updateProjectsByGuid(responseJson.projectsByGuid)
      }}
      onClose={this.props.hideModal}
      confirmCloseIfNotSaved={false}
      formSubmitUrl={url}
    >
      { formFields }
    </ModalWithForm>
  }

  handleValidation = (formData) => {
    if (!formData.name || !formData.name.trim()) {
      return { name: 'is empty' }
    }
    return {}
  }
}

const mapStateToProps = state => ({
  modalDialogState: state.modalDialogState,
  project: state.modalDialogState !== ADD_PROJECT_MODAL ? state.projectsByGuid[state.modalDialogState.modalProjectGuid] : null,
})

const mapDispatchToProps = dispatch => bindActionCreators({ updateProjectsByGuid, hideModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(AddOrEditProjectModal)
