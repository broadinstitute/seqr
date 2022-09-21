import React from 'react'
import PropTypes from 'prop-types'
import { Message } from 'semantic-ui-react'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { Select } from 'shared/components/form/Inputs'
import DataLoader from '../DataLoader'

class LoadOptionsSelect extends React.PureComponent {

  static propTypes = {
    url: PropTypes.string.isRequired,
    optionsResponseKey: PropTypes.string.isRequired,
    errorHeader: PropTypes.string,
    validationErrorHeader: PropTypes.string,
    validationErrorMessage: PropTypes.string,
  }

  state = {
    options: null,
    loading: false,
    errorHeader: null,
    error: null,
  }

  load = () => {
    const { url, errorHeader, validationErrorHeader, validationErrorMessage, optionsResponseKey } = this.props
    this.setState({ loading: true })
    new HttpRequestHelper(url,
      (responseJson) => {
        const options = responseJson[optionsResponseKey]?.map(value => ({ name: value, value }))
        if (!options || options.length === 0) {
          this.setState({
            errorHeader: validationErrorHeader,
            error: validationErrorMessage,
          })
        }
        this.setState({ loading: false, options })
      },
      (e) => {
        this.setState({ loading: false, errorHeader, error: e.message })
      }).get()
  }

  render() {
    const { options, loading, errorHeader, error } = this.state
    const errorMessage = error ? <Message visible error header={errorHeader} content={error} /> : null
    return (
      <DataLoader content={options} loading={loading} load={this.load} errorMessage={errorMessage}>
        <Select {...this.props} options={options} />
      </DataLoader>
    )
  }

}

export default LoadOptionsSelect
