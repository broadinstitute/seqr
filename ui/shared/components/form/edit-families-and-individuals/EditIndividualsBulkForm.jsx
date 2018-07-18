import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Table } from 'semantic-ui-react'
import styled from 'styled-components'
import slugify from 'slugify'

import { updateIndividuals } from 'pages/Project/reducers'
import { getProject } from 'pages/Project/selectors'
import FileUploadField from '../XHRUploaderField'
import ReduxFormWrapper from '../ReduxFormWrapper'


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

const FORM_NAME = 'bulkUploadIndividuals'
const FILE_FIELD_NAME = 'uploadedFile'
const UPLOADER_STYLE = { maxWidth: '700px', margin: 'auto' }

const BaseBulkContent = props =>
  <div>
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
                download={`individuals_for_${slugify(props.project.name, '_')}_template.xlsx`}
                href="/static/upload_tables/templates/individuals.xlsx"
              >
                blank
              </a> or &nbsp;
              <a
                download={`individuals_template_${slugify(props.project.name, '_')}.xlsx`}
                href={`/api/project/${props.project.projectGuid}/export_project_individuals?file_format=xls`}
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
                download={`individuals_template_${slugify(props.project.name, '_')}.tsv`}
                href="/static/upload_tables/templates/individuals.tsv"
              >
                blank
              </a> or &nbsp;
              <a
                download={`individuals_in_${slugify(props.project.name, '_')}_individuals.tsv`}
                href={`/api/project/${props.project.projectGuid}/export_project_individuals?file_format=tsv`}
              >
                current individuals
              </a>
            </TableCell>
          </TableRow>
        </Table.Body>
      </StyledTable>

      The table must have a header row with the following column names.<br />
      <br />
      <div>
        <BoldText>Required Columns:</BoldText><br />
        <StyledTable className="noBorder">
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
        </StyledTable>
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
            <TableRow>
              <TableCell><BoldText>HPO Terms (Present)</BoldText></TableCell>
              <TableCell>comma-separated list of HPO Terms for <i>present</i> phenotypes in this individual</TableCell>
            </TableRow>
            <TableRow>
              <TableCell><BoldText>HPO Terms (Absent)</BoldText></TableCell>
              <TableCell>comma-separated list of HPO Terms for phenotypes <i>not present</i> in this individual</TableCell>
            </TableRow>
            <TableRow>
              <TableCell><BoldText>Diagnosis: OMIM Ids</BoldText></TableCell>
              <TableCell>comma-separated list of MIM ids for disorders diagnosed in this individual</TableCell>
            </TableRow>
          </Table.Body>
        </StyledTable>
      </div>
      If the Family ID and Individual ID in the table match those of an existing individual in the project,
      the matching individual&rsquo;s data will be updated with values from the table. Otherwise, a new individual
      will be created.<br />
      <br />
    </Container>
    <br />
    <FileUploadField
      clearTimeOut={0}
      dropzoneLabel="Click here to upload a table, or drag-drop it into this box"
      url={`/api/project/${props.project.projectGuid}/upload_individuals_table`}
      auto
      required
      name={FILE_FIELD_NAME}
      uploaderStyle={UPLOADER_STYLE}
    />
    <br />
  </div>

BaseBulkContent.propTypes = {
  project: PropTypes.object,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

const BulkContent = connect(mapStateToProps)(BaseBulkContent)

const EditIndividualsBulkForm = props =>
  <ReduxFormWrapper
    form={FORM_NAME}
    modalName={props.modalName}
    submitButtonText="Apply"
    onSubmit={values => props.updateIndividuals(values[FILE_FIELD_NAME])}
    confirmCloseIfNotSaved
    closeOnSuccess
    showErrorPanel
    size="small"
    renderChildren={BulkContent}
  />

EditIndividualsBulkForm.propTypes = {
  modalName: PropTypes.string,
  updateIndividuals: PropTypes.func,
}

export { EditIndividualsBulkForm as EditIndividualsBulkFormComponent }

const mapDispatchToProps = (dispatch) => {
  return {
    updateIndividuals: values => dispatch(updateIndividuals(values)),
  }
}


export default connect(null, mapDispatchToProps)(EditIndividualsBulkForm)
