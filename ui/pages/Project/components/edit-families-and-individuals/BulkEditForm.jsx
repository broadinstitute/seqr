import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Table } from 'semantic-ui-react'

import { getCurrentProject, getUser } from 'redux/selectors'
import { FileLink } from 'shared/components/buttons/ExportTableButton'
import FileUploadField from 'shared/components/form/XHRUploaderField'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { NoBorderTable } from 'shared/components/StyledComponents'
import { INDIVIDUAL_HPO_EXPORT_DATA, FILE_FIELD_NAME } from 'shared/utils/constants'
import {
  INDIVIDUAL_ID_EXPORT_DATA,
  INDIVIDUAL_CORE_EXPORT_DATA,
  INDIVIDUAL_BULK_UPDATE_EXPORT_DATA,
  FAMILY_BULK_EDIT_EXPORT_DATA,
} from '../../constants'
import { updateFamilies, updateIndividuals, updateIndividualsHpoTerms } from '../../reducers'
import {
  getEntityExportConfig,
  getProjectAnalysisGroupFamiliesByGuid,
  getProjectAnalysisGroupIndividualsByGuid,
} from '../../selectors'

const UPLOADER_STYLES = { root: { border: '1px solid #CACACA', padding: 20, maxWidth: '700px', margin: 'auto' } }
export const BASE_UPLOAD_FORMATS = [
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


export const BaseBulkContent = React.memo(({ url, actionDescription, details, project, name, requiredFields, optionalFields, uploadFormats, exportConfig, blankExportConfig }) =>
  <div>
    <NoBorderTable compact>
      <Table.Body>
        <Table.Row>
          <Table.Cell colSpan={2}>
            To {actionDescription}, upload a table in one of these formats:
          </Table.Cell>
        </Table.Row>
        <Table.Row><Table.Cell /></Table.Row>
        {uploadFormats.map(({ title, ext, formatLinks }) =>
          <Table.Row key={title}>
            <Table.HeaderCell collapsing>
              {title} ({formatLinks ? formatLinks.map(
                ({ href, linkExt }, i) => <span key={linkExt}>{i > 0 && ' / '}<a href={href} target="_blank">.{linkExt}</a></span>)
                : `.${ext}`})
            </Table.HeaderCell>
            <Table.Cell>
              {ext &&
                <span>
                  download &nbsp;
                  {blankExportConfig &&
                  <span>
                    template: <FileLink data={blankExportConfig} ext={ext} linkContent="blank" /> &nbsp;
                  </span>
                  }
                  {exportConfig &&
                  <span>
                    {blankExportConfig && 'or'} <FileLink data={exportConfig} ext={ext} linkContent="current individuals" />
                  </span>
                  }
                </span>
              }
            </Table.Cell>
          </Table.Row>,
        )}
        <Table.Row><Table.Cell /></Table.Row>
        <Table.Row>
          <Table.Cell colSpan={2}>
            The table must have a header row with the following column names.
          </Table.Cell>
        </Table.Row>
        <Table.Row>
          <Table.HeaderCell colSpan={2}>
            Required Columns:
          </Table.HeaderCell>
        </Table.Row>
        {requiredFields.map(field =>
          <Table.Row key={field.header}>
            <Table.HeaderCell collapsing>{field.header}</Table.HeaderCell>
            <Table.Cell>{field.description}</Table.Cell>
          </Table.Row>,
        )}
        <Table.Row><Table.Cell /></Table.Row>
        <Table.Row>
          <Table.HeaderCell colSpan={2}>
            Optional Columns:
          </Table.HeaderCell>
        </Table.Row>
        {optionalFields.map(field =>
          <Table.Row key={field.header}>
            <Table.HeaderCell collapsing>{field.header}</Table.HeaderCell>
            <Table.Cell>{field.description}</Table.Cell>
          </Table.Row>,
        )}
        {details &&
        <Table.Row>
          <Table.Cell colSpan={2}>
            {details}
          </Table.Cell>
        </Table.Row>}
      </Table.Body>
    </NoBorderTable>
    <FileUploadField
      clearTimeOut={0}
      dropzoneLabel="Click here to upload a table, or drag-drop it into this box"
      url={url || `/api/project/${project.projectGuid}/upload_${name}_table`}
      auto
      required
      name={FILE_FIELD_NAME}
      styles={UPLOADER_STYLES}
    />
  </div>,
)

BaseBulkContent.propTypes = {
  url: PropTypes.string,
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

const EditBulkForm = React.memo(({ name, modalName, onSubmit, ...props }) =>
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
  </ReduxFormWrapper>,
)

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

const FamiliesBulkForm = React.memo(props =>
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
  />,
)

const mapFamiliesDispatchToProps = {
  onSubmit: updateFamilies,
}

export const EditFamiliesBulkForm = connect(mapFamiliesStateToProps, mapFamiliesDispatchToProps)(FamiliesBulkForm)

const IndividualsBulkForm = React.memo(({ user, ...props }) =>
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
    optionalFields={user.isAnalyst ? INDIVIDUAL_BULK_UPDATE_EXPORT_DATA : INDIVIDUAL_CORE_EXPORT_DATA}
    uploadFormats={FAM_UPLOAD_FORMATS}
    blankDownload
    {...props}
  />,
)

IndividualsBulkForm.propTypes = {
  user: PropTypes.object,
}

const mapIndividualsStateToProps = state => ({
  user: getUser(state),
})

const mapIndividualsDispatchToProps = {
  onSubmit: updateIndividuals,
}

export const EditIndividualsBulkForm = connect(mapIndividualsStateToProps, mapIndividualsDispatchToProps)(IndividualsBulkForm)


const HPOBulkForm = React.memo(props =>
  <EditBulkForm
    name="hpo_terms"
    actionDescription="edit individual's HPO terms"
    details="Alternately, the table can have a single row per HPO term"
    requiredFields={INDIVIDUAL_ID_EXPORT_DATA}
    optionalFields={INDIVIDUAL_HPO_EXPORT_DATA}
    uploadFormats={ALL_UPLOAD_FORMATS}
    {...props}
  />,
)

const mapHpoDispatchToProps = {
  onSubmit: updateIndividualsHpoTerms,
}

export const EditHPOBulkForm = connect(null, mapHpoDispatchToProps)(HPOBulkForm)
