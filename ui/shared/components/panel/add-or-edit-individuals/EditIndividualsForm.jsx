import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getProject, getIndividualsByGuid } from 'shared/utils/commonSelectors'
import FormWrapper from 'shared/components/form/FormWrapper'


class EditIndividualsForm extends React.PureComponent
{
  static propTypes = {
    //user: PropTypes.object.isRequired,
    individualsByGuid: PropTypes.object.isRequired,
    project: PropTypes.object,
    saveEventListener: PropTypes.func,
    closeEventListener: PropTypes.func,
  }

  constructor(props) {
    super(props)

    this.state = { uploadInProgress: false }
  }

  render() {

    return (
      <FormWrapper
        canelButtonText="Cancel"
        submitButtonText="Apply"
        onValidate={this.handleValidation}
        onSave={this.props.saveEventListener}
        onClose={this.props.closeEventListener}
        size="large"
        confirmCloseIfNotSaved={false}
        getFormDataJson={() => {}}
      >
        {
          Object.keys(this.props.individualsByGuid).map(individualGuid =>
            <input key={individualGuid} type="text" defaultValue={individualGuid} />,
          )
        }
      </FormWrapper>)
  }

  handleFileUploadStarted = () => {
    this.setState({
      uploadInProgress: true,
      onUploadResponseJson: {},
    })
  }

  handleFileUploadFinished = (responseJson) => {
    this.setState({
      uploadInProgress: false,
      onUploadResponseJson: responseJson,
    })
  }

  handleValidation = () => {
    if (this.state.uploadInProgress) {
      return { errors: [], warnings: [], info: [] }
    }

    if (!this.state.onUploadResponseJson) {
      return { errors: ['File not uploaded'] }
    }

    if (!this.state.onUploadResponseJson.token && (this.state.onUploadResponseJson.errors || this.state.onUploadResponseJson.warnings || this.state.onUploadResponseJson.info)) {
      return this.state.onUploadResponseJson
    }

    if (!this.state.onUploadResponseJson.token) {
      return { errors: [`Invalid server response: ${JSON.stringify(this.state.onUploadResponseJson)}`] }
    }

    return {
      ...this.state.onUploadResponseJson,
      formSubmitUrl: `/api/project/${this.props.project.projectGuid}/save_individuals_table/${this.state.onUploadResponseJson.token}`,
    }
  }
}

export { EditIndividualsForm as EditIndividualsFormComponent }

const mapStateToProps = state => ({
  project: getProject(state),
  individualsByGuid: getIndividualsByGuid(state),
})

export default connect(mapStateToProps)(EditIndividualsForm)
