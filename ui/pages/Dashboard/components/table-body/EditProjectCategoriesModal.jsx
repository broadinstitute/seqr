import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import ModalWithForm from 'shared/components/ModalWithForm'

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

const mapDispatchToProps = dispatch => bindActionCreators({ updateProjectsByGuid, updateProjectCategoriesByGuid, hideModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(EditProjectCategoriesModal)
