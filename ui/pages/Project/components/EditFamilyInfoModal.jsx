import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import { Form } from 'semantic-ui-react'

import ModalWithForm from '../../../shared/components/ModalWithForm'

import { EDIT_NAME_MODAL, EDIT_DESCRIPTION_MODAL } from '../constants'
import { hideModal } from '../reducers/modalDialogReducer'
import { updateFamiliesByGuid } from '../reducers/familiesByGuidReducer'


class EditProjectInfoModal extends React.PureComponent
{
  static propTypes = {
    modalDialog: React.PropTypes.object,
    project: React.PropTypes.object,
    hideModal: React.PropTypes.func.isRequired,
    updateProjectsByGuid: React.PropTypes.func.isRequired,
  }

  render() {
    if (!this.props.modalDialog || !this.props.modalDialog.modalIsVisible) {
      return null
    }

    let title = null
    let inputName = null
    let initialValue = null
    let validation = null
    switch (this.props.modalDialog.modalType) {
      case EDIT_NAME_MODAL:
        title = 'Display Name'
        inputName = 'name'
        initialValue = this.props.project.name
        validation = this.handleValidation
        break
      case EDIT_DESCRIPTION_MODAL:
        title = 'Description'
        inputName = 'description'
        initialValue = this.props.project.description
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
      <Form.Input autoFocus name={inputName} defaultValue={initialValue} />
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
  project: state.projectsByGuid[state.modalDialog.modalProjectGuid],
  modalDialog: state.modalDialog,
})

const mapDispatchToProps = dispatch => bindActionCreators({ updateProjectsByGuid, hideModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(EditProjectInfoModal)
