import React from 'react'
import PropTypes from 'prop-types'

import { Table } from 'semantic-ui-react'
import { FileLink } from 'shared/components/buttons/ExportTableButton'
import FileUploadField from 'shared/components/form/XHRUploaderField'
import { NoBorderTable } from 'shared/components/StyledComponents'
import { FILE_FIELD_NAME } from 'shared/utils/constants'

const UPLOADER_STYLES = { root: { border: '1px solid #CACACA', padding: 20, maxWidth: '700px', margin: 'auto' } }

const BulkUploadForm = React.memo(({ url, actionDescription, details, project, name, requiredFields, optionalFields, uploadFormats, exportConfig, blankExportConfig }) =>
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
                    template: <FileLink {...blankExportConfig} ext={ext} linkContent="blank" /> &nbsp;
                  </span>
                  }
                  {exportConfig &&
                  <span>
                    {blankExportConfig && 'or'} <FileLink {...exportConfig} ext={ext} linkContent="current individuals" />
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
          <Table.Row key={field.header} verticalAlign="top">
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

BulkUploadForm.propTypes = {
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

export default BulkUploadForm
