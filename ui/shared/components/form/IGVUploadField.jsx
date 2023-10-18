import PropTypes from 'prop-types'
import React from 'react'
import { Table } from 'semantic-ui-react'

import { NoBorderTable } from '../StyledComponents'
import FileUploadField, { validateUploadedFile } from './XHRUploaderField'

const IgvDropzoneLabel = ({ columns }) => (
  <NoBorderTable basic="very" compact="very">
    <Table.Body>
      <Table.Row>
        <Table.Cell colSpan={2}>
          Upload a file that maps seqr Individuals to IGV file paths. Include one row per track.
          <br />
          For merged RNA tracks, include one row for coverage and one for junctions.
        </Table.Cell>
      </Table.Row>
      <Table.Row><Table.Cell /></Table.Row>
      <Table.Row>
        <Table.HeaderCell>File Format:</Table.HeaderCell>
        <Table.Cell>Tab-separated file (.tsv) or Excel spreadsheet (.xls)</Table.Cell>
      </Table.Row>
      <Table.Row><Table.Cell /></Table.Row>
      {columns.map((column, i) => (
        <Table.Row>
          <Table.HeaderCell>{`Column ${i + 1}${i + 1 === columns.length ? ' (Optional)' : ''}:`}</Table.HeaderCell>
          <Table.Cell>{column}</Table.Cell>
        </Table.Row>
      ))}
    </Table.Body>
  </NoBorderTable>
)

IgvDropzoneLabel.propTypes = {
  columns: PropTypes.arrayOf(PropTypes.object),
}

// eslint-disable-next-line react-perf/jsx-no-new-array-as-prop
const NO_PROJECT_COLUMNS = [
  'Individual ID',
  'IGV Track File Path',
  'gCNV Sample ID, to identify the sample in the gCNV batch path. Not used for other track types',
]

// eslint-disable-next-line react-perf/jsx-no-new-array-as-prop
const COLUMNS = ['Project', ...NO_PROJECT_COLUMNS]

export const UPLOAD_IGV_FIELD = {
  name: 'mappingFile',
  validate: validateUploadedFile,
  component: FileUploadField,
  styles: { placeHolderStyle: { paddingLeft: '5%', paddingRight: '5%' } },
  dropzoneLabel: <IgvDropzoneLabel columns={COLUMNS} />,
}

export const UPLOAD_PROJECT_IGV_FIELD = {
  ...UPLOAD_IGV_FIELD,
  dropzoneLabel: <IgvDropzoneLabel columns={NO_PROJECT_COLUMNS} />,
}
