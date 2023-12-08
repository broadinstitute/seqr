/* eslint-disable jsx-a11y/no-static-element-interactions */
/* eslint-disable jsx-a11y/click-events-have-key-events */

import React from 'react'
import Cookies from 'js-cookie'
import PropTypes from 'prop-types'
import { Message } from 'semantic-ui-react'

// XHRUploader widget: https://github.com/rma-consulting/react-xhr-uploader/blob/master/src/index.js
import XHRUploader from 'react-xhr-uploader'

const NO_DISPLAY_STYLE = { display: 'none' }
const POINTER_CURSOR_STYLE = { cursor: 'pointer' }
const MAX_UNCOMPLETED_PROGRESS = 80

const onClickInput = (event) => {
  // allows the same file to be selected more than once (see
  // https://stackoverflow.com/questions/39484895/how-to-allow-input-type-file-to-select-the-same-file-in-react-component)
  event.target.value = null // eslint-disable-line no-param-reassign
}

class XHRUploaderWithEvents extends XHRUploader {

  static propTypes = {
    onUploadStarted: PropTypes.func,
    onUploadFinished: PropTypes.func,
    initialState: PropTypes.object,
    showError: PropTypes.bool,
  }

  constructor(props) {
    super(props)
    this.state = { ...this.state, ...(this.props.initialState || {}) }
  }

  setFileInputRef = (c) => { if (c) { this.fileInput = c } }

  renderInput() {
    return (
      <input
        name="file-upload"
        style={NO_DISPLAY_STYLE}
        multiple={this.props.maxFiles > 1}
        type="file"
        ref={this.setFileInputRef}
        onChange={this.onFileSelect}
        onClick={onClickInput}
      />
    )
  }

  renderButton() {
    return this.state.error && <Message error content={this.state.error} />
  }

  /**
   * Override the default implementation to call the onUpload callback with the server's response and add CSRF header
   * Taken from https://github.com/harunhasdal/react-xhr-uploader/blob/master/src/index.js
   *
   * @param file
   * @param progressCallback
   */
  uploadFile(file, progressCallback) {
    if (this.props.onUploadStarted) {
      this.props.onUploadStarted()
    }

    if (file) {
      const formData = new FormData()
      const xhr = new XMLHttpRequest()

      formData.append(this.props.fieldName, file, file.name)

      xhr.onload = () => {
        progressCallback(100)
        if (this.props.onUploadFinished) {
          if (this.props.showError && xhr.status !== 200) {
            this.setState({ error: `Error: ${xhr.statusText} (${xhr.status})` })
          } else {
            this.props.onUploadFinished(JSON.parse(xhr.response), this.state)
          }
        }
      }
      xhr.upload.onprogress = (e) => {
        const progress = e.lengthComputable ? (e.loaded / e.total * 100) : 50 // eslint-disable-line no-mixed-operators
        progressCallback(progress > MAX_UNCOMPLETED_PROGRESS ? MAX_UNCOMPLETED_PROGRESS : progress)
      }
      xhr.open(this.props.method, this.props.url, true)
      xhr.setRequestHeader('X-CSRFToken', Cookies.get('csrf_token'))
      xhr.send(formData)
      this.xhrs[file.index] = xhr
    }
  }

  cancelFileItem = item => (e) => {
    e.stopPropagation()
    this.cancelFile(item.index)
  }

  renderFileSet() {
    const { items } = this.state
    const { progressClass } = this.props
    if (items.length > 0) {
      const { cancelIconClass, completeIconClass } = this.props
      const { styles } = this.state
      const cancelledItems = items.filter(item => item.cancelled === true)
      const filesetStyle = (items.length === cancelledItems.length) ? NO_DISPLAY_STYLE : styles.fileset
      return (
        <div style={filesetStyle}>
          {
            items.filter(item => !item.cancelled).map((item) => {
              const { file } = item
              if (!file) {
                return null
              }
              const sizeInMB = (file.size / (1024 * 1024)).toPrecision(2)
              const iconClass = item.progress < 100 ? cancelIconClass : completeIconClass
              return (
                <div key={item.index}>
                  <div style={styles.fileDetails}>
                    <span className="icon-file icon-large">&nbsp;</span>
                    <span style={styles.fileName}>{`${file.name}`}</span>
                    {sizeInMB && <span style={styles.fileSize}>{`${sizeInMB} Mb`}</span>}
                    <i className={iconClass} style={POINTER_CURSOR_STYLE} onClick={this.cancelFileItem(item)} />
                  </div>
                  <div>
                    <progress
                      style={progressClass ? undefined : styles.progress}
                      className={progressClass}
                      min="0"
                      max="100"
                      value={item.progress}
                    >
                      {`${item.progress}%`}
                    </progress>
                  </div>
                </div>
              )
            })
          }
        </div>

      )
    }

    return <div />
  }

  shouldComponentUpdate(nextProps, nextState) {
    if (Object.keys(nextProps).some(k => nextProps[k] !== this.props[k])) {
      return true
    }
    return nextState !== this.state
  }

}

export default XHRUploaderWithEvents
