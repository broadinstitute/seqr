import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Table } from 'semantic-ui-react'
import styled from 'styled-components'

import { getCurrentProject } from 'redux/selectors'
import { FileLink } from 'shared/components/buttons/export-table/ExportTableButton'
import FileUploadField from 'shared/components/form/XHRUploaderField'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { INDIVIDUAL_HPO_EXPORT_DATA } from 'shared/utils/constants'
import { INDIVIDUAL_ID_EXPORT_DATA, INDIVIDUAL_CORE_EXPORT_DATA, FAMILY_BULK_EDIT_EXPORT_DATA } from '../../constants'
import { updateFamilies, updateIndividuals, updateIndividualsHpoTerms } from '../../reducers'
import {
  getEntityExportConfig,
  getProjectAnalysisGroupFamiliesByGuid,
  getProjectAnalysisGroupIndividualsByGuid,
} from '../../selectors'


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
const BASE_UPLOAD_FORMATS = [
  { title: 'Excel', ext: 'xls' },
  {
    title: 'Text',
    ext: 'tsv',
    formatLinks: [
      { href: 'https://en.wikipedia.org/wiki/Tab-separated_values', linkExt: 'tsv' },
      { href: 'https://en.wikipedia.org/wiki/Comma-separated_values', linkExt: 'csv' },
    ] },
]
const ALL_UPLOAD_FORMATS = BASE_UPLOAD_FORMATS.concat([
  { title: 'Phenotips Export', formatLinks: [{ href: 'https://phenotips.org/', linkExt: 'json' }] },
])
const FAM_UPLOAD_FORMATS = [].concat(BASE_UPLOAD_FORMATS)
FAM_UPLOAD_FORMATS[1] = { ...FAM_UPLOAD_FORMATS[1], formatLinks: [...FAM_UPLOAD_FORMATS[1].formatLinks, { href: 'https://www.cog-genomics.org/plink2/formats#fam', linkExt: 'fam' }] }


const BaseBulkContent = ({ actionDescription, details, project, name, requiredFields, optionalFields, uploadFormats, exportConfig, blankExportConfig }) =>
  <div>
    <Container>
      To {actionDescription}, upload a table in one of these formats:
      <StyledTable>
        <Table.Body>
          {uploadFormats.map(({ title, ext, formatLinks }) =>
            <TableRow key={title}>
              <TableCell>
                <BoldText>{title}</BoldText> ({formatLinks ? formatLinks.map(
                  ({ href, linkExt }, i) => <span key={linkExt}>{i > 0 && ' / '}<a href={href} target="_blank">.{linkExt}</a></span>)
                  : `.${ext}`})
              </TableCell>
              <TableCell>
                {ext &&
                  <span>
                    download &nbsp;
                    {blankExportConfig &&
                      <span>
                      template: <FileLink data={blankExportConfig} ext={ext} linkContent="blank" /> or&nbsp;
                      </span>
                    }
                    <FileLink data={exportConfig} ext={ext} linkContent="current individuals" />
                  </span>
                }
              </TableCell>
            </TableRow>,
          )}
        </Table.Body>
      </StyledTable>

      The table must have a header row with the following column names.<br />
      <br />
      <div>
        <BoldText>Required Columns:</BoldText><br />
        <StyledTable>
          <Table.Body>
            {requiredFields.map(field =>
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
            {optionalFields.map(field =>
              <TableRow key={field.header}>
                <TableCell><BoldText>{field.header}</BoldText></TableCell>
                <TableCell>{field.description}</TableCell>
              </TableRow>,
            )}
          </Table.Body>
        </StyledTable>
      </div>
      {details && <div><br />{details}</div>}
      <br />
    </Container>
    <br />
    <FileUploadField
      clearTimeOut={0}
      dropzoneLabel="Click here to upload a table, or drag-drop it into this box"
      url={`/api/project/${project.projectGuid}/upload_${name}_table`}
      auto
      required
      name={FILE_FIELD_NAME}
      uploaderStyle={UPLOADER_STYLE}
    />
  </div>

BaseBulkContent.propTypes = {
  actionDescription: PropTypes.string.isRequired,
  requiredFields: PropTypes.array.isRequired,
  optionalFields: PropTypes.array.isRequired,
  uploadFormats: PropTypes.array,
  details: PropTypes.node,
  name: PropTypes.string.isRequired,
  project: PropTypes.object,
  exportConfig: PropTypes.object,
  blankExportConfig: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  project: getCurrentProject(state),
  exportConfig: getEntityExportConfig(
    getCurrentProject(state),
    Object.values(ownProps.rawData || getProjectAnalysisGroupIndividualsByGuid(state, ownProps)),
    null,
    ownProps.name,
    ownProps.requiredFields.concat(ownProps.optionalFields),
  ),
  blankExportConfig: ownProps.blankDownload && getEntityExportConfig(getCurrentProject(state), [], null, 'template', ownProps.requiredFields.concat(ownProps.optionalFields)),
})

const BulkContent = connect(mapStateToProps)(BaseBulkContent)

const EditBulkForm = ({ name, modalName, onSubmit, ...props }) =>
  <ReduxFormWrapper
    form={`bulkUpload_${name}`}
    modalName={modalName}
    onSubmit={values => onSubmit(values[FILE_FIELD_NAME])}
    confirmCloseIfNotSaved
    closeOnSuccess
    showErrorPanel
    liveValidate
    size="small"
  >
    <BulkContent name={name} {...props} />
  </ReduxFormWrapper>

EditBulkForm.propTypes = {
  name: PropTypes.string.isRequired,
  modalName: PropTypes.string.isRequired,
  onSubmit: PropTypes.func.isRequired,
}

const FAMILY_ID_EXPORT_DATA = FAMILY_BULK_EDIT_EXPORT_DATA.slice(0, 1)
const FAMILY_EXPORT_DATA = FAMILY_BULK_EDIT_EXPORT_DATA.slice(1)

const mapFamiliesStateToProps = (state, ownProps) => ({
  rawData: getProjectAnalysisGroupFamiliesByGuid(state, ownProps),
})

const FamiliesBulkForm = props =>
  <EditBulkForm
    name="families"
    actionDescription="bulk-add or edit families"
    details={
      <div>
        If the Family ID in the table matches those of an existing family in the project,
        the matching families&apos;s data will be updated with values from the table. Otherwise, a new family
        will be created. To edit an existing families&apos;s ID include a <b>Previous Family ID</b> column.
      </div>
    }
    requiredFields={FAMILY_ID_EXPORT_DATA}
    optionalFields={FAMILY_EXPORT_DATA}
    uploadFormats={BASE_UPLOAD_FORMATS}
    blankDownload
    {...props}
  />

const mapFamiliesDispatchToProps = {
  onSubmit: updateFamilies,
}

export const EditFamiliesBulkForm = connect(mapFamiliesStateToProps, mapFamiliesDispatchToProps)(FamiliesBulkForm)

const IndividualsBulkForm = props =>
  <EditBulkForm
    name="individuals"
    actionDescription="bulk-add or edit individuals"
    details={
      <div>
        If the Family ID and Individual ID in the table match those of an existing individual in the project,
        the matching individual&apos;s data will be updated with values from the table. Otherwise, a new individual
        will be created. To edit an existing individual&apos;s ID include a <b>Previous Individual ID</b> column.
      </div>
    }
    requiredFields={INDIVIDUAL_ID_EXPORT_DATA}
    optionalFields={INDIVIDUAL_CORE_EXPORT_DATA}
    uploadFormats={FAM_UPLOAD_FORMATS}
    blankDownload
    {...props}
  />

const mapIndividualsDispatchToProps = {
  onSubmit: updateIndividuals,
}

export const EditIndividualsBulkForm = connect(null, mapIndividualsDispatchToProps)(IndividualsBulkForm)


const HPOBulkForm = props =>
  <EditBulkForm
    name="hpo_terms"
    actionDescription="edit individual's HPO terms"
    details="Alternately, the table can have a single row per HPO term"
    requiredFields={INDIVIDUAL_ID_EXPORT_DATA}
    optionalFields={INDIVIDUAL_HPO_EXPORT_DATA}
    uploadFormats={ALL_UPLOAD_FORMATS}
    {...props}
  />

const mapHpoDispatchToProps = {
  onSubmit: updateIndividualsHpoTerms,
}

export const EditHPOBulkForm = connect(null, mapHpoDispatchToProps)(HPOBulkForm)
