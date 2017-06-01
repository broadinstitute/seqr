import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import Dropzone from 'react-dropzone'
import request from 'superagent'

import { getProject } from 'shared/utils/commonReducers'

import ModalWithForm from 'shared/components/modal/ModalWithForm'

import {
  getEditFamiliesAndIndividualsModalIsVisible,
  hideEditFamiliesAndIndividualsModal,
} from './state'


class EditFamiliesAndIndividualsModal extends React.PureComponent
{
  static propTypes = {
    isVisible: PropTypes.bool.isRequired,

    project: PropTypes.object,
    hideModal: PropTypes.func.isRequired,
  }

  render() {
    if (!this.props.isVisible) {
      return null
    }

    const formFields = [/*
      <Form.Input key={1} label="Project Name" name="name" placeholder="Name" autoFocus />,
      <Form.Input key={2} label="Project Description" name="description" placeholder="Description" />,
    */]

    return <ModalWithForm
      title={`Edit Families And Individuals: ${this.props.project.deprecatedProjectId} `}
      submitButtonText={'Save'}
      onValidate={this.handleValidation}
      onSave={(responseJson) => {
        console.log('EditFamiliesAndIndividualsModal response', responseJson)
      }}
      onClose={() => {
        this.props.hideModal()
        //window.location.reload()  // refresh the current page after phenotips edits
      }}
      size="large"
      confirmCloseIfNotSaved={false}
      formSubmitUrl={'/api/project/create_project'}
    >
      <div style={{ textAlign: 'left', width: '100%' }}>
        Please use this template: <a href="/template">Individuals And Families Template</a>
         and upload it (or another Excel (.xls), or tab-delimited text table (.tsv) file) <br />
        with the following columns:<br />
        <br />
        <b>Family ID * </b><br />
        <b>Participant ID * </b><br />
        <b>Father Participant ID * </b><br />
        <b>Mother Participant ID * </b><br />
        <b>Sex</b> (M = Male, F = Female)<br />
        <b>Is Affected?</b> (A = Affected, U = unaffected) whether this individual has the condition<br />
        <b>Notes</b> free text notes related to this individual<br />
        <b>HPO Terms * </b>{'comma-separated list of HPO IDs (for example: "HP:0002354")'}<br />
        <br />
        * = required
        <br />
        <br />
      </div>
      <center>
        <Dropzone height="50px" accept=".xls,.xslx,.ped" onDrop={
          (acceptedFiles) => {
            const req = request.post(`/api/project/${this.props.project.projectGuid}/upload_families_and_individuals_table`)
            acceptedFiles.map(file => req.attach(file.name, file))
            req.end((err, res) => {
              console.log(err)
              console.log(res)
            })
          }
        }
        >
          {({ isDragActive, isDragReject }) => {
            if (isDragActive) {
              return ''
            }
            if (isDragReject) {
              return 'Invalid file type.'
            }
            return 'Click or drag-drop an .xls, .xlsx, or .tsv file here...'
          }}
        </Dropzone>
      </center>
      { formFields }

    </ModalWithForm>
  }

  handleValidation = () => {  //formData
    /*
    if ((!formData.name || !formData.name.trim())) {
      return { name: 'is empty' }
    }
    */
    return {}
  }
}

export { EditFamiliesAndIndividualsModal as EditFamiliesAndIndividualsModalComponent }

const mapStateToProps = state => ({
  isVisible: getEditFamiliesAndIndividualsModalIsVisible(state),
  project: getProject(state),
})

const mapDispatchToProps = {
  hideModal: hideEditFamiliesAndIndividualsModal,
}

export default connect(mapStateToProps, mapDispatchToProps)(EditFamiliesAndIndividualsModal)
