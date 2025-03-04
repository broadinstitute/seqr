import React from 'react'
import PropTypes from 'prop-types'
import { Header } from 'semantic-ui-react'

import { HttpRequestHelper } from '../../utils/httpRequestHelper'
import UploadFormPage from './UploadFormPage'

class SubmitFormPage extends React.PureComponent {

  static propTypes = {
    fields: PropTypes.arrayOf(PropTypes.object),
    header: PropTypes.string,
    url: PropTypes.string,
  }

  state = { uploadStats: {} }

  onSubmit = (values) => {
    const { url } = this.props
    return new HttpRequestHelper(url,
      (uploadStats) => {
        this.setState({ uploadStats })
      }, (error) => {
        if (error?.body) {
          this.setState({ uploadStats: error.body })
        }
        return Promise.reject(error)
      }).post(values)
  }

  render() {
    const { header, fields } = this.props
    const { uploadStats } = this.state
    return (
      <div>
        <Header size="medium" textAlign="center" content={header} />
        <UploadFormPage fields={fields} uploadStats={uploadStats} onSubmit={this.onSubmit} />
      </div>
    )
  }

}

export default SubmitFormPage
