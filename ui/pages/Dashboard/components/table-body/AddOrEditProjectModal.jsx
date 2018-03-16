import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Form } from 'semantic-ui-react'

import ModalWithForm from 'shared/components/modal/ModalWithForm'

import { EDIT_NAME_MODAL, EDIT_DESCRIPTION_MODAL, ADD_PROJECT_MODAL, EDIT_PROJECT_MODAL, DELETE_PROJECT_MODAL } from '../../constants'
import { hideModal, updateProjectsByGuid } from '../../../../redux/rootReducer'

class AddOrEditProjectModal extends React.PureComponent
{
  static propTypes = {
    modalDialogState: PropTypes.object.isRequired,
    project: PropTypes.object,
    hideModal: PropTypes.func.isRequired,
    updateProjectsByGuid: PropTypes.func.isRequired,
  }

  constructor() {
    super()

    this.formDataJson = {}
  }

  render() {
    if (!this.props.modalDialogState || !this.props.modalDialogState.modalIsVisible) {
      return null
    }

    let title = null
    let formFields = null
    let validate = true
    let url = null
    let submitButtonText = null
    switch (this.props.modalDialogState.modalType) {
      case EDIT_NAME_MODAL:
        title = 'Edit Project Name'
        this.formDataJson.name = this.props.project.name
        formFields = <Form.Input
          autoFocus
          name="name"
          defaultValue={this.props.project.name}
          onChange={(event, data) => {
            this.formDataJson.name = data.value
          }}
        />
        url = `/api/project/${this.props.project.projectGuid}/update_project`
        break
      case EDIT_DESCRIPTION_MODAL:
        title = 'Edit Project Description'
        this.formDataJson.description = this.props.project.description
        formFields = <Form.Input
          autoFocus
          name="description"
          onChange={(event, data) => {
            this.formDataJson.description = data.value
          }}
          defaultValue={this.props.project.description}
        />
        validate = false
        url = `/api/project/${this.props.project.projectGuid}/update_project`
        break
      case ADD_PROJECT_MODAL:
        title = 'Create Project'
        this.formDataJson.name = ''
        this.formDataJson.description = ''
        formFields = [
          <Form.Input
            key={1}
            label="Project Name"
            name="name"
            placeholder="Name"
            onChange={(event, data) => {
              this.formDataJson.name = data.value
            }}
            autoFocus
          />,
          <Form.Input
            key={2}
            label="Project Description"
            name="description"
            placeholder="Description"
            onChange={(event, data) => {
              this.formDataJson.description = data.value
            }}
          />,
        ]
        url = '/api/project/create_project'
        break
      case EDIT_PROJECT_MODAL:
        title = 'Edit Project'
        this.formDataJson.name = this.props.project.name
        this.formDataJson.description = this.props.project.description
        formFields = [
          <Form.Input
            key={1}
            label="Project Name"
            name="name"
            placeholder="Name"
            onChange={(event, data) => {
              this.formDataJson.name = data.value
            }}
            autoFocus
            defaultValue={this.props.project.name}
          />,
          <Form.Input
            key={2}
            label="Project Description"
            name="description"
            onChange={(event, data) => {
              this.formDataJson.description = data.value
            }}
            placeholder="Description"
            defaultValue={this.props.project.description}
          />,
        ]
        url = `/api/project/${this.props.project.projectGuid}/update_project`
        break
      case DELETE_PROJECT_MODAL:
        if (!this.props.project) {
          return null // prevent null exception during the extra render after a project is deleted
        }
        title = 'Delete Project?'
        formFields = (
          <div style={{ textAlign: 'left' }}>
            Are you sure you want to delete project <b>{this.props.project.name}</b>?
          </div>)
        validate = false
        url = `/api/project/${this.props.project.projectGuid}/delete_project`
        submitButtonText = 'Yes'
        break
      default:
        return null
    }

    return (
      <ModalWithForm
        title={title}
        submitButtonText={submitButtonText}
        performClientSideValidation={validate ? this.performValidation : null}
        handleSave={(responseJson) => {
          this.props.updateProjectsByGuid(responseJson.projectsByGuid)
        }}

        handleClose={this.props.hideModal}
        confirmCloseIfNotSaved={false}
        formSubmitUrl={url}
        getFormDataJson={() => this.formDataJson}
      >
        { formFields }
      </ModalWithForm>)
  }

  performValidation = (formData) => {
    if (!formData.name || !formData.name.trim()) {
      return {
        errors: ['Name is empty'],
      }
    }
    return {}
  }
}

export { AddOrEditProjectModal as AddOrEditProjectModalComponent }

const mapStateToProps = state => ({
  modalDialogState: state.modalDialogState,
  project: state.modalDialogState.modalType !== ADD_PROJECT_MODAL ? state.projectsByGuid[state.modalDialogState.modalProjectGuid] : null,
})

const mapDispatchToProps = {
  updateProjectsByGuid,
  hideModal,
}

export default connect(mapStateToProps, mapDispatchToProps)(AddOrEditProjectModal)
