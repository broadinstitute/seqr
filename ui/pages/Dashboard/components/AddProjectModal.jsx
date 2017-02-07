import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import { Form, Dropdown } from 'semantic-ui-react'

import ModalWithForm from '../../../shared/components/ModalWithForm'
import { ADD_PROJECT_MODAL } from '../constants'

import { hideModal, updateProjectsByGuid, updateProjectCategoriesByGuid } from '../reducers/rootReducer'


class AddProjectModal extends React.PureComponent
{
  static propTypes = {
    modalDialogState: React.PropTypes.object,
    hideModal: React.PropTypes.func.isRequired,
    updateProjectsByGuid: React.PropTypes.func.isRequired,
    updateProjectCategoriesByGuid: React.PropTypes.func.isRequired,
  }

  render() {
    if (!this.props.modalDialogState || !this.props.modalDialogState.modalIsVisible || this.props.modalDialogState.modalType !== ADD_PROJECT_MODAL) {
      return null
    }

    return <ModalWithForm
      title={'Create Project'}
      //onValidate={validation}
      onSave={(responseJson) => {
        this.props.updateProjectsByGuid(responseJson.projectsByGuid)
        this.props.updateProjectCategoriesByGuid(responseJson.projectCategoriesByGuid)
      }}
      onClose={this.props.hideModal}
      confirmCloseIfNotSaved={false}
      formSubmitUrl="/api/project/create_project"
    >
      <div style={{ textAlign: 'left' }}>
        <Form.Input label="Project Name" name="name" placeholder="Project Name" />
        <Form.Input label="Project Description" name="description" placeholder="Project Description" />
        <br />
        <Dropdown label="Type of Data" placeholder="Data Type" fluid selection options={[
          { text: 'Exome', value: 'exome' },
          { text: 'Genome', value: 'genome' },
          { text: 'RNA-seq', value: 'rna' }]}
        />
      </div>

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
})

const mapDispatchToProps = dispatch => bindActionCreators({ updateProjectsByGuid, updateProjectCategoriesByGuid, hideModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(AddProjectModal)
