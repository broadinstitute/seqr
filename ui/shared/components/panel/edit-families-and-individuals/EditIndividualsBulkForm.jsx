import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Table } from 'semantic-ui-react'
import styled from 'styled-components'

import slugify from 'slugify'

import {
  getProject,
  getUser,
  updateFamiliesByGuid,
  updateIndividualsByGuid,
} from 'redux/utils/commonDataActionsAndSelectors'
import XHRUploaderWithEvents from 'shared/components/form/XHRUploaderWithEvents'
import FormWrapper from 'shared/components/form/FormWrapper'
import MessagesPanel from 'shared/components/form/MessagesPanel'

const Container = styled.div`
  textAlign: left;
  width: 100%;
  padding: 5px 15px 5px 35px;
`

const BoldText = styled.span`
  font-weight: 600
`

const StyledTable = styled(Table)`
  padding: 5px 0px 5px 25px !important;
  border: none !important;
`

const TableRow = styled(Table.Row)`
  border-top: none !important;
`

const TableCell = styled(Table.Cell)`
  padding: 2px 5px 2px 0px !important;
  border-top: none !important;
  vertical-align: top;
`

/*
const tdStyle = {
  padding: '2px 5px 2px 0px',
  verticalAlign: 'top',
}
*/

class EditIndividualsBulkForm extends React.PureComponent
{
  static propTypes = {
    //user: PropTypes.object.isRequired,
    project: PropTypes.object,
    onSave: PropTypes.func,
    onClose: PropTypes.func,
    updateIndividualsByGuid: PropTypes.func.isRequired,
    updateFamiliesByGuid: PropTypes.func.isRequired,
  }

  static DEFAULT_STATE = {
    errors: [],
    warnings: [],
    info: [],
    uploadedFileId: null,
  }

  constructor(props) {
    super(props)

    this.state = EditIndividualsBulkForm.DEFAULT_STATE
  }

  render() {

    return (
      <FormWrapper
        submitButtonText="Apply"
        performClientSideValidation={this.performValidation}
        handleSave={this.props.onSave}
        handleClose={this.props.onClose}
        confirmCloseIfNotSaved={false}
        getFormDataJson={() => {}}
        formSubmitUrl={
          this.state.uploadedFileId ?
            `/api/project/${this.props.project.projectGuid}/save_individuals_table/${this.state.uploadedFileId}`
            : null
        }
      >
        <Container>
          To bulk-add or edit individuals, upload a table in one of these formats:
          <StyledTable>
            <Table.Body>
              <TableRow>
                <TableCell>
                  <BoldText>Excel</BoldText> (.xls)
                </TableCell>
                <TableCell>
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
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell>
                  <BoldText>Text</BoldText> (<a href="https://en.wikipedia.org/wiki/Tab-separated_values" target="_blank" rel="noopener noreferrer">.tsv</a> / <a href="https://www.cog-genomics.org/plink2/formats#fam" target="_blank" rel="noopener noreferrer">.fam</a>)
                </TableCell>
                <TableCell>
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
                </TableCell>
              </TableRow>
            </Table.Body>
          </StyledTable>

          The table must have a header row with the following column names.<br />
          <br />
          <div style={{ padding: '3px 0px 5px 25px' }}>
            <BoldText>Required Columns:</BoldText><br />
            <Table className="noBorder" style={{ padding: '3px 0px 5px 25px' }}>
              <Table.Body>
                <TableRow>
                  <TableCell><BoldText>Family ID</BoldText></TableCell>
                  <TableCell />
                </TableRow>
                <TableRow>
                  <TableCell><BoldText>Individual ID</BoldText></TableCell>
                  <TableCell />
                </TableRow>
              </Table.Body>
            </Table>
            <BoldText>Optional Columns:</BoldText>
            <StyledTable>
              <Table.Body>
                <TableRow>
                  <TableCell><BoldText>Paternal ID</BoldText></TableCell>
                  <TableCell><i>Individual ID</i> of the father</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell><BoldText>Maternal ID</BoldText></TableCell>
                  <TableCell><i>Individual ID</i> of the mother</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell><BoldText>Sex</BoldText></TableCell>
                  <TableCell><BoldText>M</BoldText> = Male, <BoldText>F</BoldText> = Female, and leave blank if unknown</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell><BoldText>Affected Status</BoldText></TableCell>
                  <TableCell><BoldText>A</BoldText> = Affected, <BoldText>U</BoldText> = Unaffected, and leave blank if unknown</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell><BoldText>Notes</BoldText></TableCell>
                  <TableCell>free-text notes related to this individual</TableCell>
                </TableRow>
                {/*
                <TableRow>
                  <TableCell><BoldText>Indication for referral</BoldText></TableCell>
                  <TableCell>indication for referral</TableCell>
                </TableRow>

                <TableRow>
                  <TableCell><BoldText>HPO Terms - present</BoldText></TableCell>
                  <TableCell>
                    comma-separated list of HPO IDs present in this individual&rsquo;s phenotype (eg. <i>&quot;HP:0002354, HP:0002355&quot;</i>)
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell><BoldText>HPO Terms - absent</BoldText></TableCell>
                  <TableCell>
                    comma-separated list of HPO IDs absent from this individual&rsquo;s phenotype (eg. <i>&quot;HP:0002354, HP:0002355&quot;</i>)
                  </TableCell>
                </TableRow>
                */}
                {/*
                <TableRow>
                  <TableCell><BoldText>Funding Source</BoldText></TableCell>
                  <TableCell>funding source for this study (eg. &quot;NHLBI&quot;)</TableCell>
                </TableRow>
                */}
                {/*
                  this.props.user.is_staff &&
                  <TableRow>
                    <TableCell><BoldText>In Case Review</BoldText></TableCell>
                    <TableCell>
                      Case Review Status
                    </TableCell>
                  </TableRow>
                */}
              </Table.Body>
            </StyledTable>
          </div>
          If the Family ID and Individual ID in the table match those of an existing individual in the project,
          the matching individual&rsquo;s data will be updated with values from the table. Otherwise, a new individual
          will be created.<br />
          <br />
        </Container>
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
        <MessagesPanel errors={this.state.errors} warnings={this.state.warnings} info={this.state.info} />
      </FormWrapper>)
  }

  handleFileUploadStarted = () => {
    this.setState(EditIndividualsBulkForm.DEFAULT_STATE)
  }

  handleFileUploadFinished = (responseJson) => {
    this.setState({
      errors: responseJson.errors,
      warnings: responseJson.warnings,
      info: responseJson.info,
      uploadedFileId: responseJson.uploadedFileId,
    })
  }

  performValidation = () => {
    if (!this.state.uploadedFileId) {
      this.setState({
        errors: ['File not uploaded'],
      })

      return {
        preventSubmit: true,
      }
    }

    return {
      preventSubmit: this.state.errors && this.state.errors.length > 0,
    }
  }

  handleFormSaved = (responseJson) => {
    if (this.props.onSave) {
      this.props.onSave(responseJson)
    }
    /**
     * NOTE: families are also updated here because each family object contains a list of
     * individualGuids for the individuals in the family, and these lists have to be updated
     * to remove deleted individuals.
     */
    this.props.updateIndividualsByGuid(responseJson.individualsByGuid)
    this.props.updateFamiliesByGuid(responseJson.familiesByGuid)
  }
}

export { EditIndividualsBulkForm as EditIndividualsBulkFormComponent }

const mapStateToProps = state => ({
  project: getProject(state),
  user: getUser(state),
})

const mapDispatchToProps = {
  updateIndividualsByGuid,
  updateFamiliesByGuid,
}

export default connect(mapStateToProps, mapDispatchToProps)(EditIndividualsBulkForm)
