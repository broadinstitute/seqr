import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import ProjectCategoriesInput from './ProjectCategoriesInput'
import ModalWithForm from '../../../shared/components/ModalWithForm'
import { EDIT_CATEGORY_MODAL } from '../constants'

import { hideModal, updateProjectsByGuid, updateProjectCategoriesByGuid } from '../reducers/rootReducer'


class EditProjectCategoriesModal extends React.PureComponent
{
  static propTypes = {
    modalDialogState: React.PropTypes.object,
    project: React.PropTypes.object,
    hideModal: React.PropTypes.func.isRequired,
    updateProjectsByGuid: React.PropTypes.func.isRequired,
    updateProjectCategoriesByGuid: React.PropTypes.func.isRequired,
  }

  render() {
    if (!this.props.modalDialogState || !this.props.modalDialogState.modalIsVisible || this.props.modalDialogState.modalType !== EDIT_CATEGORY_MODAL) {
      return null
    }

    return <ModalWithForm
      title={'Project Categories'}
      //onValidate={validation}
      onSave={(responseJson) => {
        this.props.updateProjectsByGuid(responseJson.projectsByGuid)
        this.props.updateProjectCategoriesByGuid(responseJson.projectCategoriesByGuid)
      }}
      onClose={this.props.hideModal}
      confirmCloseIfNotSaved={false}
      formSubmitUrl={`/api/project/${this.props.project.projectGuid}/update_project_categories`}
    >
      <ProjectCategoriesInput project={this.props.project} />
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

const mapDispatchToProps = dispatch => bindActionCreators({ updateProjectsByGuid, updateProjectCategoriesByGuid, hideModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(EditProjectCategoriesModal)
