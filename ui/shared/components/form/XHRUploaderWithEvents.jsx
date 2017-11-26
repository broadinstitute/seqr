/* eslint-disable jsx-a11y/no-static-element-interactions */
/* eslint-disable jsx-a11y/click-events-have-key-events */

import React from 'react'
import PropTypes from 'prop-types'

//XHRUploader widget: https://github.com/rma-consulting/react-xhr-uploader/blob/master/src/index.js
import XHRUploader from 'react-xhr-uploader'

class XHRUploaderWithEvents extends XHRUploader {

  static propTypes = {
    onUploadStarted: PropTypes.func,
    onUploadFinished: PropTypes.func,
  }

  renderInput() {
    return <input
      name="file-upload"
      style={{ display: 'none' }}
      multiple={this.props.maxFiles > 1}
      type="file" ref={(c) => { if (c) { this.fileInput = c } }}
      onChange={this.onFileSelect}
      onClick={(event) => { event.target.value = null }} // allows the same file to be selected more than once (see https://stackoverflow.com/questions/39484895/how-to-allow-input-type-file-to-select-the-same-file-in-react-component)
    />
  }

  /**
   * Override the default implementation to call the onUpload callback with the server's response.
   * @param file
   * @param progressCallback
   */
  uploadFile(file, progressCallback) {
    if (this.props.onUploadStarted) {
      this.props.onUploadStarted()
    }

    super.uploadFile(file, progressCallback)

    if (this.xhrs) {
      const xhr = Object.values(this.xhrs)[0]
      const originalOnLoad = xhr.onload

      xhr.onload = (e) => {
        const responseJson = this.processResponse(xhr)
        if (this.props.onUploadFinished) {
          this.props.onUploadFinished(responseJson)
        }
        originalOnLoad(e)
      }
    }
  }


  renderFileSet() {
    const { items } = this.state
    const { progressClass } = this.props
    if (items.length > 0) {
      const { cancelIconClass, completeIconClass } = this.props
      const { progress, styles } = this.state
      const cancelledItems = items.filter(item => item.cancelled === true)
      const filesetStyle = (items.length === cancelledItems.length) ? { display: 'none' } : styles.fileset
      return (
        <div style={filesetStyle}>
          {
            items.filter(item => !item.cancelled).map((item) => {
              const { file } = item
              if (!file) {
                console.log('not a file', this.state.items)
                return null
              }

              const sizeInMB = (file.size / (1024 * 1024)).toPrecision(2)
              const iconClass = item.progress < 100 ? cancelIconClass : completeIconClass
              return (
                <div key={item.index}>
                  <div style={styles.fileDetails}>
                    <span className="icon-file icon-large">&nbsp;</span>
                    <span style={styles.fileName}>{`${file.name}`}</span> {/* , ${file.type} */}
                    {sizeInMB && <span style={styles.fileSize}>{`${sizeInMB} Mb`}</span>}

                    <i
                      className={iconClass}
                      style={{ cursor: 'pointer' }}
                      onClick={(e) => {
                        e.stopPropagation()
                        this.cancelFile(item.index)
                      }}
                    />
                  </div>
                  <div>
                    <progress
                      style={progressClass ? {} : styles.progress}
                      className={progressClass} min="0" max="100"
                      value={item.progress}
                    >
                      {item.progress}%
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

  /**
   * Process the server's response after the file is uploaded. Return an object that looks like
   *   {
   *      errors: [], warnings: [], info: []
   *   }
   *
   * @param xhr XMLHttpRequest object
   */
  processResponse = (xhr) => {
    if (xhr.status !== 200) {
      return {
        errors: [`${xhr.status} ${xhr.statusText}`],
      }
    }

    const responseJson = JSON.parse(xhr.response)

    return responseJson
  }
}

export default XHRUploaderWithEvents
