import React from 'react'
import { connect } from 'react-redux'
import { List, Segment } from 'semantic-ui-react'

import FileUploadField, { validateUploadedFile } from 'shared/components/form/XHRUploaderField'
import UploadFormPage from 'shared/components/page/UploadFormPage'

import { getIgvUploadStats } from '../selectors'
import { addIgv } from '../reducers'

const mapStateToProps = state => ({
  fields: [
    {
      name: 'mappingFile',
      validate: validateUploadedFile,
      component: FileUploadField,
      dropzoneLabel: (
        <Segment basic textAlign="left">
          Upload a file with desired IGV tracks. Include one row per track.
          For merged RNA tracks, include one row for coverage and one for junctions.
          <br />
          Columns are as follows:
          <br />
          <List ordered>
            <List.Item>Project</List.Item>
            <List.Item>Individual ID</List.Item>
            <List.Item>IGV Track File Path</List.Item>
            <List.Item>
              Optional: Sample ID if different from Individual ID.
              Used primarily for gCNV files to identify the sample in the batch path
            </List.Item>
          </List>
        </Segment>
      ),
    },
  ],
  uploadStats: getIgvUploadStats(state),
})

const mapDispatchToProps = {
  onSubmit: addIgv,
}

export default connect(mapStateToProps, mapDispatchToProps)(UploadFormPage)
