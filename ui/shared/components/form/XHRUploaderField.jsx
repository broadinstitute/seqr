import React from 'react'
import PropTypes from 'prop-types'
import { Field } from 'react-final-form'
import { Message, Loader } from 'semantic-ui-react'
import styled from 'styled-components'

const XHRUploaderWithEvents = React.lazy(() => import('./XHRUploaderWithEvents'))

const MessagePanel = styled(Message)`
  margin: 2em !important;
`

class UploaderFieldComponent extends React.PureComponent {

  static propTypes = {
    input: PropTypes.object,
    uploaderProps: PropTypes.object,
  }

  onStarted = () => {
    const { input } = this.props
    input.onChange({ loading: true })
  }

  onFinished = (xhrResponse, uploaderState) => {
    const { input } = this.props
    input.onChange({ uploaderState, ...xhrResponse })
  }

  render() {
    const { input, uploaderProps } = this.props
    const { url = '/api/upload_temp_file', returnParsedData, ...uploaderComponentProps } = uploaderProps
    const path = returnParsedData ? '?parsedData=true' : ''
    return ([
      <React.Suspense key="uploader" fallback={<Loader />}>
        <XHRUploaderWithEvents
          onUploadStarted={this.onStarted}
          onUploadFinished={this.onFinished}
          initialState={input.value ? input.value.uploaderState : null}
          url={`${url}${path}`}
          clearTimeOut={0}
          auto
          {...uploaderComponentProps}
          maxFiles={1}
        />
      </React.Suspense>,
      (input.value && input.value.info) ? <MessagePanel key="info" info visible list={input.value.info} /> : null,
    ])
  }

}

export const uploadedFileHasErrors = (value) => {
  if (value?.errors && value.errors.length) {
    return value.errors
  }
  if (value?.loading) {
    return 'File upload incomplete'
  }
  return undefined
}
const hasUploadedFile = value => (value && value.uploadedFileId ? undefined : 'File not uploaded')
export const validateUploadedFile = value => uploadedFileHasErrors(value) || hasUploadedFile(value)
export const warnUploadedFile = value => value && value.warnings && (value.warnings.length ? value.warnings : undefined)

const UploaderFormField = React.memo(({ name, required, onChange, parse, ...props }) => (
  <Field
    name={name}
    validate={required ? validateUploadedFile : uploadedFileHasErrors}
    warn={warnUploadedFile}
    uploaderProps={props}
    component={UploaderFieldComponent}
    onChange={onChange}
    parse={parse}
  />
))

UploaderFormField.propTypes = {
  name: PropTypes.string.isRequired,
  required: PropTypes.bool,
  onChange: PropTypes.func,
  parse: PropTypes.func,
}

export default UploaderFormField
