import React from 'react'
import XHRUploader from 'react-xhr-uploader'
import { Field } from 'redux-form'


class XHRUploaderWithCallbacks extends XHRUploader {

  renderInput() {
    // allows the same file to be selected more than once (see https://stackoverflow.com/questions/39484895/how-to-allow-input-type-file-to-select-the-same-file-in-react-component)
    return React.cloneElement(super.renderInput(), { onClick: (event) => { event.target.value = null } })
  }

  updateFileProgress(index, progress) {
    super.updateFileProgress(index, progress)
    if (progress === 100) {
      const xhr = Object.values(this.xhrs)[0]
      this.props.onUploaded(xhr)
    }
  }
}

const required = value => (value ? undefined : 'File not uploaded')
const noErrors = value => (value.errors ? value.errors : undefined)

export default props =>
  <Field
    name="uploadedFileId"
    validate={[required, noErrors]}
    uploaderProps={props}
    component={({ uploaderProps, input }) => {
      return (
        <XHRUploaderWithCallbacks
          onUploaded={(xhr) => {
            const response = JSON.parse(xhr.response)
            if (xhr.status !== 200) {
              input.onChange(response)
            } else {
              input.onChange(response[input.name])
            }
          }}
          {...uploaderProps}
          maxFiles={1}
        />
      )
    }}
  />
