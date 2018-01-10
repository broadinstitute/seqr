import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import ModalWithForm from 'shared/components/modal/ModalWithForm'

import ProjectCategoriesInput from './ProjectCategoriesInput'
import { EDIT_CATEGORY_MODAL } from '../../constants'

import {
  getProjectsByGuid,
  getModalDialogState,
  getModalProjectGuid,
  hideModal,
  updateProjectsByGuid,
  updateProjectCategoriesByGuid,
} from '../../redux/rootReducer'


class EditProjectCategoriesModal extends React.PureComponent
{
  static propTypes = {
    modalDialogState: PropTypes.object,
    project: PropTypes.object,
    hideModal: PropTypes.func.isRequired,
    updateProjectsByGuid: PropTypes.func.isRequired,
    updateProjectCategoriesByGuid: PropTypes.func.isRequired,
  }

  constructor() {
    super()

    this.formDataJson = {}
  }

  render() {
    if (!this.props.modalDialogState || !this.props.modalDialogState.modalIsVisible || this.props.modalDialogState.modalType !== EDIT_CATEGORY_MODAL) {
      return null
    }

    return (
      <ModalWithForm
        title="Edit Project Categories"
        handleSave={(responseJson) => {
          this.props.updateProjectsByGuid(responseJson.projectsByGuid)
          this.props.updateProjectCategoriesByGuid(responseJson.projectCategoriesByGuid)
        }}
        handleClose={this.props.hideModal}
        confirmCloseIfNotSaved={false}
        getFormDataJson={() => this.formDataJson}
        formSubmitUrl={`/api/project/${this.props.project.projectGuid}/update_project_categories`}
      >
        <ProjectCategoriesInput project={this.props.project} onChange={(categories) => {
          this.formDataJson.categories = categories
        }}
        />
      </ModalWithForm>)
  }
}

export { EditProjectCategoriesModal as EditProjectCategoriesModalComponent }

const mapStateToProps = state => ({
  project: getProjectsByGuid(state)[getModalProjectGuid(state)],
  modalDialogState: getModalDialogState(state),
})

const mapDispatchToProps = {
  updateProjectsByGuid,
  updateProjectCategoriesByGuid,
  hideModal,
}

export default connect(mapStateToProps, mapDispatchToProps)(EditProjectCategoriesModal)
