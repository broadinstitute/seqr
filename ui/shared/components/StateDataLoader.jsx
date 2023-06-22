import React from 'react'
import PropTypes from 'prop-types'
import { Message } from 'semantic-ui-react'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import DataLoader from './DataLoader'

class StateDataLoader extends React.PureComponent {

  static propTypes = {
    url: PropTypes.string.isRequired,
    childComponent: PropTypes.elementType.isRequired,
    parseResponse: PropTypes.func.isRequired,
    validateResponse: PropTypes.func,
    errorHeader: PropTypes.string,
    validationErrorHeader: PropTypes.string,
    validationErrorMessage: PropTypes.string,
  }

  state = {
    loadedProps: null,
    loading: false,
    errorHeader: null,
    error: null,
  }

  load = () => {
    const {
      url, errorHeader, validationErrorHeader, validationErrorMessage, parseResponse, validateResponse,
    } = this.props
    this.setState({ loading: true })
    new HttpRequestHelper(url,
      (responseJson) => {
        const loadedProps = parseResponse(responseJson)
        if (validateResponse && !validateResponse(loadedProps)) {
          this.setState({
            errorHeader: validationErrorHeader,
            error: validationErrorMessage,
          })
        }
        this.setState({ loading: false, loadedProps })
      },
      (e) => {
        this.setState({ loading: false, errorHeader, error: e.message })
      }).get()
  }

  render() {
    const { loadedProps, loading, errorHeader, error } = this.state
    const {
      childComponent, url, validationErrorHeader, validationErrorMessage, parseResponse, validateResponse, ...props
    } = this.props
    const errorMessage = error ? <Message visible error header={errorHeader} content={error} /> : null
    return (
      <DataLoader content={loadedProps} loading={loading} load={this.load} errorMessage={errorMessage}>
        {React.createElement(childComponent, { ...props, ...loadedProps })}
      </DataLoader>
    )
  }

}

export default StateDataLoader
