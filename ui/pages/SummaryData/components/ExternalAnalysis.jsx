import React from 'react'
import { connect } from 'react-redux'

import { validators } from 'shared/components/form/FormHelpers'
import { Select } from 'shared/components/form/Inputs'
import FileUploadField, { validateUploadedFile } from 'shared/components/form/XHRUploaderField'
import UploadFormPage from 'shared/components/page/UploadFormPage'
import { FAMILY_ANALYSED_BY_DATA_TYPES } from 'shared/utils/constants'

import { getExternalAnalysisUploadStats } from '../selectors'
import { updateExternalAnalysis } from '../reducers'

const UPLOAD_FIELDS = [
  {
    name: 'dataType',
    label: 'Data Type',
    component: Select,
    options: [
      ...FAMILY_ANALYSED_BY_DATA_TYPES.map(([value, text]) => ({ value, text })),
      { value: 'AIP' },
    ],
    validate: validators.required,
  },
  {
    name: 'familiesFile',
    component: FileUploadField,
    dropzoneLabel: (
      <div>
        Drag-drop or click here to upload analysed families
        <br />
        <br />
        File should include a &quot;Project&quot; and a &quot;Family&quot; column OR be valid AIP JSON
      </div>
    ),
    validate: validateUploadedFile,
  },
]

const mapStateToProps = state => ({
  fields: UPLOAD_FIELDS,
  uploadStats: getExternalAnalysisUploadStats(state),
})

const mapDispatchToProps = {
  onSubmit: updateExternalAnalysis,
}

export default connect(mapStateToProps, mapDispatchToProps)(UploadFormPage)
