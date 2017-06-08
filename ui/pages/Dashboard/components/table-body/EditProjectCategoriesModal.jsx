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
} from '../../reducers/rootReducer'


class EditProjectCategoriesModal extends React.PureComponent
{
  static propTypes = {
    modalDialogState: PropTypes.object,
    project: PropTypes.object,
    hideModal: PropTypes.func.isRequired,
    updateProjectsByGuid: PropTypes.func.isRequired,
    updateProjectCategoriesByGuid: PropTypes.func.isRequired,
  }

  render() {
    if (!this.props.modalDialogState || !this.props.modalDialogState.modalIsVisible || this.props.modalDialogState.modalType !== EDIT_CATEGORY_MODAL) {
      return null
    }

    return <ModalWithForm
      title={'Edit Project Categories'}
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
