import React from 'react'
import PropTypes from 'prop-types'

import { Form } from 'semantic-ui-react'
import { connect } from 'react-redux'

import ModalWithForm from 'shared/components/modal/ModalWithForm'
import { updateProject } from 'shared/utils/commonActions'

import { getEditProjectModalIsVisible, getEditProjectModalProject, hideEditProjectModal } from './state'


class EditProjectModal extends React.PureComponent
{
  static propTypes = {
    isVisible: PropTypes.bool.isRequired,
    project: PropTypes.object,
    updateProject: PropTypes.func.isRequired,
    hideEditProjectModal: PropTypes.func.isRequired,
  }

  constructor() {
    super()

    this.formDataJson = {}
  }

  render() {

    if (!this.props.isVisible) {
      return null
    }

    const { project } = this.props

    this.formDataJson.name = project.name
    this.formDataJson.description = project.description

    return (
      <ModalWithForm
        title="Edit Project"
        formSubmitUrl={`/api/project/${project.projectGuid}/update_project`}
        submitButtonText="Save"
        onValidate={(formData) => {
          if (!formData.name || !formData.name.trim()) {
            return { errors: { name: 'name is empty' } }
          }
          return {}
        }}
        getFormDataJson={() => this.formDataJson}
        onSave={(responseJson) => {
          this.props.updateProject(responseJson.projectsByGuid[project.projectGuid])
        }}
        onClose={this.props.hideEditProjectModal}
        size="large"
        confirmCloseIfNotSaved={false}
      >
        <Form.Input
          key={1}
          label="Project Name"
          name="name"
          placeholder="Name"
          autoFocus
          defaultValue={project.name}
          onChange={(event, data) => {
            this.formDataJson.name = data.value
          }}
        />,
        <Form.Input
          key={2}
          label="Project Description"
          name="description"
          placeholder="Description"
          defaultValue={project.description}
          onChange={(event, data) => {
            this.formDataJson.description = data.value
          }}
        />
      </ModalWithForm>)
  }
}


const mapStateToProps = state => ({
  isVisible: getEditProjectModalIsVisible(state),
  project: getEditProjectModalProject(state),
})

const mapDispatchToProps = {
  updateProject,
  hideEditProjectModal,
}

export default connect(mapStateToProps, mapDispatchToProps)(EditProjectModal)

