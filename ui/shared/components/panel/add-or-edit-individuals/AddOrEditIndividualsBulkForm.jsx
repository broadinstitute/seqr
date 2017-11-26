import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Table, Icon } from 'semantic-ui-react'

import slugify from 'slugify'

import { getProject, getUser } from 'shared/utils/commonSelectors'
import XHRUploaderWithEvents from 'shared/components/form/XHRUploaderWithEvents'
import FormWrapper from 'shared/components/form/FormWrapper'

const tdStyle = {
  padding: '2px 5px 2px 0px',
  verticalAlign: 'top',
}

class AddOrEditIndividualsBulkForm extends React.PureComponent
{
  static propTypes = {
    user: PropTypes.object.isRequired,
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
        <div style={{ textAlign: 'left', width: '100%', paddingLeft: '25px' }}>
          To bulk-add or edit individuals, upload a table in one of these formats:
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

          The table must have a header row with the following column names.<br />
          <br />
          <div style={{ padding: '3px 0px 5px 25px' }}>
            <b>Required Columns:</b><br />
            <Table className="noBorder" style={{ padding: '3px 0px 5px 25px' }}>
              <Table.Body>
                <Table.Row className="noBorder">
                  <Table.Cell className="noBorder" style={{ minWidth: '10em', ...tdStyle }}><b>Family ID</b></Table.Cell>
                  <Table.Cell className="noBorder" style={tdStyle} />
                </Table.Row>
                <Table.Row className="noBorder">
                  <Table.Cell className="noBorder" style={tdStyle}><b>Individual ID</b></Table.Cell>
                  <Table.Cell className="noBorder" style={tdStyle} />
                </Table.Row>
              </Table.Body>
            </Table>
            <b>Optional Columns:</b>
            <Table className="noBorder" style={{ padding: '3px 0px 5px 25px' }}>
              <Table.Body>
                <Table.Row className="noBorder">
                  <Table.Cell className="noBorder" style={{ minWidth: '10em', ...tdStyle }}><b>Paternal ID</b></Table.Cell>
                  <Table.Cell className="noBorder" style={tdStyle}>the <i>Individual ID</i> of the father</Table.Cell>
                </Table.Row>
                <Table.Row className="noBorder">
                  <Table.Cell className="noBorder" style={tdStyle}><b>Maternal ID</b></Table.Cell>
                  <Table.Cell className="noBorder" style={tdStyle}>the <i>Individual ID</i> of the mother</Table.Cell>
                </Table.Row>
                <Table.Row className="noBorder">
                  <Table.Cell className="noBorder" style={tdStyle}><b>Sex</b></Table.Cell>
                  <Table.Cell className="noBorder" style={tdStyle}><b>M</b> = Male, <b>F</b> = Female, and leave blank if unknown</Table.Cell>
                </Table.Row>
                <Table.Row className="noBorder">
                  <Table.Cell className="noBorder" style={tdStyle}><b>Affected Status</b></Table.Cell>
                  <Table.Cell className="noBorder" style={tdStyle}><b>A</b> = Affected, <b>U</b> = Unaffected, and leave blank if unknown</Table.Cell>
                </Table.Row>
                <Table.Row className="noBorder">
                  <Table.Cell className="noBorder" style={tdStyle}><b>Notes</b></Table.Cell>
                  <Table.Cell className="noBorder" style={tdStyle}>free-text notes related to this individual</Table.Cell>
                </Table.Row>
                {/*
                <Table.Row>
                  <Table.Cell className="noBorder" style={tdStyle}><b>Indication for referral</b></Table.Cell>
                  <Table.Cell className="noBorder" style={tdStyle}>indication for referral</Table.Cell>
                </Table.Row>
                */}
                <Table.Row>
                  <Table.Cell className="noBorder" style={tdStyle}><b>HPO Terms - present</b></Table.Cell>
                  <Table.Cell className="noBorder" style={tdStyle}>
                    comma-separated list of HPO IDs present in this individual&rsquo;s phenotype (eg. <i>&quot;HP:0002354, HP:0002355&quot;</i>)
                  </Table.Cell>
                </Table.Row>
                <Table.Row>
                  <Table.Cell className="noBorder" style={tdStyle}><b>HPO Terms - absent</b></Table.Cell>
                  <Table.Cell className="noBorder" style={tdStyle}>
                    comma-separated list of HPO IDs absent from this individual&rsquo;s phenotype (eg. <i>&quot;HP:0002354, HP:0002355&quot;</i>)
                  </Table.Cell>
                </Table.Row>
                {/*
                <Table.Row className="noBorder">
                  <Table.Cell className="noBorder" style={tdStyle}><b>Funding Source</b></Table.Cell>
                  <Table.Cell className="noBorder" style={tdStyle}>funding source for this study (eg. &quot;NHLBI&quot;)</Table.Cell>
                </Table.Row>
                */}
                {
                  this.props.user.is_staff &&
                  <Table.Row className="noBorder">
                    <Table.Cell className="noBorder" style={tdStyle}><b>Case Review Status</b></Table.Cell>
                    <Table.Cell className="noBorder" style={tdStyle}>
                      Case Review Status
                    </Table.Cell>
                  </Table.Row>
                }
              </Table.Body>
            </Table>
          </div>
          If the Family ID and Individual ID in the table match those of an existing individual in the project,
          the matching individual&rsquo;s data will be updated with values from the table. Otherwise, a new individual
          will be created.<br />
          <br />
        </div>
        <br />
        <div style={{ maxWidth: '700px', margin: 'auto' }}>
          <XHRUploaderWithEvents
            clearTimeOut={0}
            dropzoneLabel="Click here to upload a table, or drag-drop it into this box"
            method="POST"
            url={`/api/project/${this.props.project.projectGuid}/upload_individuals_table`}
            auto
            maxFiles={1}
            maxSize={25 * 1024 * 1024}
            onUploadStarted={this.handleFileUploadStarted}
            onUploadFinished={this.handleFileUploadFinished}
          />
        </div>
        <br />
        <div>
          {
            this.state.uploadInProgress &&
            <span>
              <br />
              <Icon loading name="spinner" /> Processing file
              <br />
            </span>
          }
        </div>
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

export { AddOrEditIndividualsBulkForm as AddOrEditIndividualsBulkFormComponent }

const mapStateToProps = state => ({
  project: getProject(state),
  user: getUser(state),
})

export default connect(mapStateToProps)(AddOrEditIndividualsBulkForm)
