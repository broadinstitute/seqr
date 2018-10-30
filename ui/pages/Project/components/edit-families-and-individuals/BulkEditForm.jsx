import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Table } from 'semantic-ui-react'
import styled from 'styled-components'

import { FileLink } from 'shared/components/buttons/export-table/ExportTableButton'
import FileUploadField from 'shared/components/form/XHRUploaderField'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { INDIVIDUAL_ID_EXPORT_DATA, INDIVIDUAL_CORE_EXPORT_DATA } from '../../constants'
import { updateIndividuals } from '../../reducers'
import { getProject, getEntityExportConfig, getProjectAnalysisGroupIndividualsByGuid } from '../../selectors'


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

const FILE_FIELD_NAME = 'uploadedFile'
const UPLOADER_STYLE = { maxWidth: '700px', margin: 'auto' }
const UPLOAD_FORMATS = [
  { name: 'Excel', ext: 'xls' },
  { name: 'Text', ext: 'tsv', detail: <a href="https://en.wikipedia.org/wiki/Tab-separated_values" target="_blank">.tsv</a> / <a href="https://www.cog-genomics.org/plink2/formats#fam" target="_blank">.fam</a> },
]


const BaseBulkContent = ({ actionDescription, details, url, project, individualFields, individualsExportConfig, blankIndividualsExportConfig }) =>
  <div>
    <Container>
      To {actionDescription}, upload a table in one of these formats:
      <StyledTable>
        <Table.Body>
          {UPLOAD_FORMATS.map(({ name, ext, detail }) =>
            <TableRow key={ext}>
              <TableCell>
                <BoldText>{name}</BoldText> ({detail || `.${ext}`})
              </TableCell>
              <TableCell>
                download
                {blankIndividualsExportConfig &&
                  <span>
                    &nbsp;template: <FileLink data={blankIndividualsExportConfig} ext={ext} linkContent="blank" /> or&nbsp;
                  </span>
                }
                <FileLink data={individualsExportConfig} ext={ext} linkContent="current individuals" />
              </TableCell>
            </TableRow>,
          )}
        </Table.Body>
      </StyledTable>

      The table must have a header row with the following column names.<br />
      <br />
      <div>
        <BoldText>Required Columns:</BoldText><br />
        <StyledTable className="noBorder">
          <Table.Body>
            {INDIVIDUAL_ID_EXPORT_DATA.map(field =>
              <TableRow key={field.header}>
                <TableCell><BoldText>{field.header}</BoldText></TableCell>
                <TableCell />
              </TableRow>,
            )}
          </Table.Body>
        </StyledTable>
        <BoldText>Optional Columns:</BoldText>
        <StyledTable>
          <Table.Body>
            {individualFields.map(field =>
              <TableRow key={field.header}>
                <TableCell><BoldText>{field.header}</BoldText></TableCell>
                <TableCell>{field.description}</TableCell>
              </TableRow>,
            )}
          </Table.Body>
        </StyledTable>
      </div>
      {details}
      <br />
    </Container>
    <br />
    <FileUploadField
      clearTimeOut={0}
      dropzoneLabel="Click here to upload a table, or drag-drop it into this box"
      url={url && url(project)}
      auto
      required
      name={FILE_FIELD_NAME}
      uploaderStyle={UPLOADER_STYLE}
    />
    <br />
  </div>

BaseBulkContent.propTypes = {
  actionDescription: PropTypes.string.isRequired,
  individualFields: PropTypes.array.isRequired,
  details: PropTypes.string,
  url: PropTypes.func,
  project: PropTypes.object,
  individualsExportConfig: PropTypes.object,
  blankIndividualsExportConfig: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  project: getProject(state),
  individualsExportConfig: getEntityExportConfig(getProject(state), Object.values(getProjectAnalysisGroupIndividualsByGuid(state, ownProps)), null, 'individuals', INDIVIDUAL_ID_EXPORT_DATA.concat(ownProps.individualFields)),
  blankIndividualsExportConfig: ownProps.blankDownload && getEntityExportConfig(getProject(state), [], null, 'template', INDIVIDUAL_ID_EXPORT_DATA.concat(ownProps.individualFields)),
})

const BulkContent = connect(mapStateToProps)(BaseBulkContent)

const EditBulkForm = ({ form, modalName, onSubmit, ...props }) =>
  <ReduxFormWrapper
    form={form}
    modalName={modalName}
    onSubmit={values => onSubmit(values[FILE_FIELD_NAME])}
    confirmCloseIfNotSaved
    closeOnSuccess
    showErrorPanel
    size="small"
    renderChildren={() => <BulkContent {...props} />}
  />

EditBulkForm.propTypes = {
  form: PropTypes.string,
  modalName: PropTypes.string,
  onSubmit: PropTypes.func,
}

const IndividualsBulkForm = props =>
  <EditBulkForm
    form="bulkUploadIndividuals"
    actionDescription="bulk-add or edit individuals"
    details="If the Family ID and Individual ID in the table match those of an existing individual in the project,
      the matching individual's data will be updated with values from the table. Otherwise, a new individual
      will be created."
    individualFields={INDIVIDUAL_CORE_EXPORT_DATA}
    url={project => `/api/project/${project.projectGuid}/upload_individuals_table`}
    blankDownload
    {...props}
  />

const mapDispatchToProps = {
  onSubmit: updateIndividuals,
}


export const EditIndividualsBulkForm = connect(null, mapDispatchToProps)(IndividualsBulkForm)
