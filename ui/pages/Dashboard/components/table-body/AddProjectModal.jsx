import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Form, Modal, Icon } from 'semantic-ui-react'

import FormWrapper from 'shared/components/form/FormWrapper'

import { updateProjectsByGuid } from 'redux/rootReducer'

class AddProjectModal extends React.PureComponent
{
  static propTypes = {
    trigger: PropTypes.node,
    updateProjectsByGuid: PropTypes.func.isRequired, // TODO should dispatch a save event instead
  }

  state = {
    modalOpen: false,
    formDataJson: {
      name: '',
      description: '',
    },
  }

  handleOpen = () => this.setState({ modalOpen: true })

  handleClose = () => this.setState({ modalOpen: false })

  render() {
    const trigger = React.cloneElement(this.props.trigger, { onClick: this.handleOpen })
    return (
      <Modal size="small" open={this.state.modalOpen} trigger={trigger}>
        <Modal.Header>
          <span style={{ fontSize: '15px' }}>Create Project</span>
          <a role="button" tabIndex="0" style={{ float: 'right', cursor: 'pointer' }} onClick={this.handleClose}>
            <Icon name="remove" style={{ fontSize: '15px', color: '#A3A3A3' }} />
          </a>
        </Modal.Header>
        <Modal.Content style={{ textAlign: 'center' }}>
          <FormWrapper
            getFormDataJson={() => this.state.formDataJson}
            formSubmitUrl="/api/project/create_project"
            performClientSideValidation={this.performValidation}
            handleSave={(responseJson) => {
              this.props.updateProjectsByGuid(responseJson.projectsByGuid)
            }}
            handleClose={this.handleClose}
            confirmCloseIfNotSaved={false}
          >
            <Form.Input
              key={1}
              label="Project Name"
              name="name"
              placeholder="Name"
              onChange={(event, data) => {
                this.state.formDataJson.name = data.value
              }}
              autoFocus
            />
            <Form.Input
              key={2}
              label="Project Description"
              name="description"
              placeholder="Description"
              onChange={(event, data) => {
                this.state.formDataJson.description = data.value
              }}
            />
          </FormWrapper>
        </Modal.Content>
      </Modal>
    )
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

const mapDispatchToProps = {
  updateProjectsByGuid,
}

export default connect(null, mapDispatchToProps)(AddProjectModal)
