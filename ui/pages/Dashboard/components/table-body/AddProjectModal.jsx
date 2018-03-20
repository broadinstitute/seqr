import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import Modal from 'shared/components/modal/Modal'
import ButtonPanel from 'shared/components/form/ButtonPanel'
import RequestStatus from 'shared/components/form/RequestStatus'
import { saveProject } from 'redux/rootReducer'

import { Field, reduxForm } from 'redux-form'
import { Form } from 'semantic-ui-react'

/* eslint-disable react/prop-types */
const required = value => (value ? undefined : 'Required')

const renderField = (props) => {
  const { meta: { touched, invalid }, input, ...additionalProps } = props
  return <Form.Input error={touched && invalid} {...input} {...additionalProps} />
}

let ProjectForm = (props) => {
  const { submitting, submitFailed, submitSucceeded, invalid, error, handleSubmit } = props
  let saveStatus = RequestStatus.NONE
  if (submitSucceeded) {
    saveStatus = RequestStatus.SUCCEEDED
  } else if (submitFailed) {
    saveStatus = RequestStatus.ERROR
  }
  const saveErrorMessage = error || (invalid ? 'Invalid input' : 'Unknown')

  return (
    <Form onSubmit={handleSubmit} loading={submitting}>
      <Field component={renderField} name="name" label="Project Name" placeholder="Name" validate={[required]} />
      <Field component={renderField} name="description" label="Project Description" placeholder="Description" />
      <ButtonPanel saveStatus={saveStatus} saveErrorMessage={saveErrorMessage} />
    </Form>
  )
}
//
// ProjectForm.propTypes = {
//   handleSubmit: PropTypes.func,
//   onSubmit: PropTypes.func,
// }

ProjectForm = reduxForm()(ProjectForm)

class AddProjectModal extends React.PureComponent
{
  static propTypes = {
    trigger: PropTypes.node,
  }

  state = {
    // formDataJson: {
    //   name: '',
    //   description: '',
    // },
  }

  // <FormWrapper
  //           getFormDataJson={() => this.state.formDataJson}
  //           formSubmitUrl="/api/project/create_project"
  //           performClientSideValidation={this.performValidation}
  //           handleSave={(responseJson) => {
  //             this.props.updateProjectsByGuid(responseJson.projectsByGuid)
  //           }}
  //           handleClose={this.handleClose}
  //           confirmCloseIfNotSaved={false}
  //         >
  //           <Form.Input
  //             key={1}
  //             label="Project Name"
  //             name="name"
  //             placeholder="Name"
  //             onChange={(event, data) => {
  //               this.state.formDataJson.name = data.value
  //             }}
  //             autoFocus
  //           />
  //           <Form.Input
  //             key={2}
  //             label="Project Description"
  //             name="description"
  //             placeholder="Description"
  //             onChange={(event, data) => {
  //               this.state.formDataJson.description = data.value
  //             }}
  //           />
  //         </FormWrapper>

  render() {
    return (
      <Modal trigger={this.props.trigger} title="Create Project" >
        <ProjectForm onSubmit={this.props.saveProject} form="addProject" />
      </Modal>
    )
  }

  submit = (values) => {
    console.log(values)
  }

  // validate = (values) => {
  //
  // }

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
  saveProject,
}

export default connect(null, mapDispatchToProps)(AddProjectModal)
// export default AddProjectModal
