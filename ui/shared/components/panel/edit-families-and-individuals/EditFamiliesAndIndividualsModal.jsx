import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Table, Icon } from 'semantic-ui-react'

import slugify from 'slugify'

import { getProject } from 'shared/utils/commonReducers'
import XHRUploaderWithEvents from 'shared/components/form/XHRUploaderWithEvents'
import ModalWithForm from 'shared/components/modal/ModalWithForm'

import {
  getEditFamiliesAndIndividualsModalIsVisible,
  hideEditFamiliesAndIndividualsModal,
} from './state'

const tdStyle = {
  padding: '2px 5px 2px 0px',
}

class EditFamiliesAndIndividualsModal extends React.PureComponent
{
  static propTypes = {
    isVisible: PropTypes.bool.isRequired,

    project: PropTypes.object,
    hideModal: PropTypes.func.isRequired,
  }

  constructor(props) {
    super(props)

    this.state = { uploadInProgress: false }
  }

  render() {
    if (!this.props.isVisible) {
      return null
    }

    /*
    const formFields = [
      <Form.Input key={1} label="Project Name" name="name" placeholder="Name" autoFocus />,
      <Form.Input key={2} label="Project Description" name="description" placeholder="Description" />,
    ]
    */
    return <ModalWithForm
      title={'Add or Edit Individuals'}
      submitButtonText={'Apply'}
      onValidate={this.handleValidation}
      onSave={this.handleSave}
      onClose={this.handleClose}
      size="large"
      confirmCloseIfNotSaved={false}
    >
      {/* use this template: <a href="/template">Individuals And Families Template</a> and upload it (or another Excel (.xls), or tab-delimited text table (.tsv) file) <br /> */}
      <div style={{ textAlign: 'left', width: '100%', paddingLeft: '25px' }}>

        To add or edit individuals, upload a table in one of these formats:
        <Table className="noBorder" style={{ padding: '5px 0px 5px 25px' }}>
          <Table.Body>
            <Table.Row className="noBorder">
              <Table.Cell className="noBorder" style={tdStyle}>
                <b>Excel</b> (.xls)
              </Table.Cell>
              <Table.Cell className="noBorder" style={tdStyle}>
                download template: &nbsp;
                <a
                  download={`individuals_for_${slugify(this.props.project.name, '_')}_template.xlsx`}
                  href="/static/upload_tables/templates/individuals.xlsx"
                >
                  blank
                </a> or &nbsp;
                <a
                  download={`individuals_template_${slugify(this.props.project.name, '_')}.xlsx`}
                  href={`/api/project/${this.props.project.projectGuid}/export_project_individuals?file_format=xls`}
                >
                  current individuals
                </a>
              </Table.Cell>
            </Table.Row>
            <Table.Row className="noBorder">
              <Table.Cell className="noBorder" style={tdStyle}>
                <b>Text</b> (<a href="https://en.wikipedia.org/wiki/Tab-separated_values" target="_blank" rel="noopener noreferrer">.tsv</a> / <a href="https://www.cog-genomics.org/plink2/formats#fam" target="_blank" rel="noopener noreferrer">.fam</a>)
              </Table.Cell>
              <Table.Cell className="noBorder" style={tdStyle}>
                download template: &nbsp;
                <a
                  download={`individuals_template_${slugify(this.props.project.name, '_')}.tsv`}
                  href="/static/upload_tables/templates/individuals.tsv"
                >
                  blank
                </a> or &nbsp;
                <a
                  download={`individuals_in_${slugify(this.props.project.name, '_')}_individuals.tsv`}
                  href={`/api/project/${this.props.project.projectGuid}/export_project_individuals?file_format=tsv`}
                >
                  current individuals
                </a>
              </Table.Cell>
            </Table.Row>
          </Table.Body>
        </Table>

        The table should contain these columns (* = required):
        <Table className="noBorder" style={{ padding: '3px 0px 5px 25px' }}>
          <Table.Body>
            <Table.Row className="noBorder">
              <Table.Cell className="noBorder" style={tdStyle}><b>Family ID * </b></Table.Cell>
              <Table.Cell className="noBorder" style={tdStyle} />
            </Table.Row>
            <Table.Row className="noBorder">
              <Table.Cell className="noBorder" style={tdStyle}><b>Individual ID * </b></Table.Cell>
              <Table.Cell className="noBorder" style={tdStyle} />
            </Table.Row>
            <Table.Row className="noBorder">
              <Table.Cell className="noBorder" style={tdStyle}><b>Paternal ID</b></Table.Cell>
              <Table.Cell className="noBorder" style={tdStyle} />
            </Table.Row>
            <Table.Row className="noBorder">
              <Table.Cell className="noBorder" style={tdStyle}><b>Maternal ID</b></Table.Cell>
              <Table.Cell className="noBorder" style={tdStyle} />
            </Table.Row>
            <Table.Row className="noBorder">
              <Table.Cell className="noBorder" style={tdStyle}><b>Sex</b></Table.Cell>
              <Table.Cell className="noBorder" style={tdStyle}><b>M</b> = Male, <b>F</b> = Female, and leave blank if sex is unknown</Table.Cell>
            </Table.Row>
            <Table.Row className="noBorder">
              <Table.Cell className="noBorder" style={tdStyle}><b>Affected Status</b></Table.Cell>
              <Table.Cell className="noBorder" style={tdStyle}><b>A</b> = Affected, <b>U</b> = Unaffected, and leave blank if status is unknown</Table.Cell>
            </Table.Row>
            <Table.Row className="noBorder">
              <Table.Cell className="noBorder" style={tdStyle}><b>Notes</b></Table.Cell>
              <Table.Cell className="noBorder" style={tdStyle}>free-text notes related to this individual</Table.Cell>
            </Table.Row>
            {/*<Table.Row><Table.Cell className="noBorder" style={tdStyle}><b>HPO Terms</b></Table.Cell><Table.Cell className="noBorder" style={tdStyle}>{'comma-separated list of HPO IDs (eg. "HP:0002354, HP:0002355")'}</Table.Cell></Table.Row>*/}
          </Table.Body>
        </Table>

        If an individual ID in the table matches the ID of an existing individual in the project,<br />
        values from the table will be used to modify the existing individual.<br />
        <br />
      </div>
      <center>
        <XHRUploaderWithEvents
          clearTimeOut={0}
          dropzoneLabel="Click here or upload a table, or drag-drop it into this box"
          method="POST"
          url={`/api/project/${this.props.project.projectGuid}/upload_individuals_table`}
          auto
          maxFiles={1}
          maxSize={25 * 1024 * 1024}
          onUploadStarted={this.handleFileUploadStarted}
          onUploadFinished={this.handleFileUploadFinished}
        />
      </center>
      <div>
        {
          this.state.uploadInProgress && <span>
            <br />
            <Icon loading name="spinner" /> Processing file
            <br />
          </span>
        }
      </div>
    </ModalWithForm>
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
      return { errors: ['File not uploaded yet'] }
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

  handleSave = (responseJson) => {
    console.log('EditFamiliesAndIndividualsModal response', responseJson)
    window.location.reload()  // refresh the current page TODO update data directly
  }

  handleClose = () => {
    this.props.hideModal()
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
