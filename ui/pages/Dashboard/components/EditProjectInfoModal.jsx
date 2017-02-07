import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import { Form } from 'semantic-ui-react'

import ModalWithForm from '../../../shared/components/ModalWithForm'

import { EDIT_NAME_MODAL, EDIT_DESCRIPTION_MODAL } from '../constants'
import { hideModal, updateProjectsByGuid } from '../reducers/rootReducer'

class EditProjectInfoModal extends React.PureComponent
{
  static propTypes = {
    modalDialogState: React.PropTypes.object,
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
    switch (this.props.modalDialogState.modalType) {
      case EDIT_NAME_MODAL:
        title = 'Project Name'
        formFields = <Form.Input autoFocus name={'name'} defaultValue={this.props.project.name} />
        validation = this.handleValidation
        break
      case EDIT_DESCRIPTION_MODAL:
        title = 'Project Description'
        formFields = <Form.Input autoFocus name={'description'} defaultValue={this.props.project.description} />
        break
      default:
        return null
    }

    return <ModalWithForm
      title={title}
      onValidate={validation}
      onSave={(responseJson) => {
        const updatedProjectsByGuid = responseJson
        this.props.updateProjectsByGuid(updatedProjectsByGuid)
      }}
      onClose={this.props.hideModal}
      confirmCloseIfNotSaved={false}
      formSubmitUrl={`/api/project/${this.props.project.projectGuid}/update_project_info`}
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
  project: state.projectsByGuid[state.modalDialogState.modalProjectGuid],
  modalDialogState: state.modalDialogState,
})

const mapDispatchToProps = dispatch => bindActionCreators({ updateProjectsByGuid, hideModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(EditProjectInfoModal)
