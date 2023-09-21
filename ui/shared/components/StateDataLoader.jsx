import React from 'react'
import PropTypes from 'prop-types'
import { Message } from 'semantic-ui-react'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import FormWrapper from './form/FormWrapper'
import DataLoader from './DataLoader'

class StateDataLoader extends React.PureComponent {

  static propTypes = {
    url: PropTypes.string,
    childComponent: PropTypes.elementType.isRequired,
    parseResponse: PropTypes.func.isRequired,
    validateResponse: PropTypes.func,
    errorHeader: PropTypes.string,
    validationErrorHeader: PropTypes.string,
    validationErrorMessage: PropTypes.string,
    queryFields: PropTypes.arrayOf(PropTypes.object),
  }

  state = {
    loadedProps: null,
    loading: false,
    errorHeader: null,
    error: null,
  }

  componentDidUpdate(prevProps) {
    const { url } = this.props
    if (prevProps.url !== url) {
      this.load()
    }
  }

  load = (query) => {
    const {
      url, errorHeader, validationErrorHeader, validationErrorMessage, parseResponse, validateResponse,
    } = this.props
    if (!url) {
      this.setState({ showEmpty: true })
      return
    }
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
      }).get(query)
  }

  render() {
    const { loadedProps, loading, errorHeader, error, showEmpty } = this.state
    const {
      childComponent, url, validationErrorHeader, validationErrorMessage, parseResponse, validateResponse, queryFields,
      ...props
    } = this.props
    const errorMessage = error ? <Message visible error header={errorHeader} content={error} /> : null
    const queryForm = queryFields && (
      <FormWrapper
        onSubmit={this.load}
        fields={queryFields}
        noModal
        inline
        submitOnChange
      />
    )
    return (
      <DataLoader content={loadedProps || showEmpty} loading={loading} load={this.load} errorMessage={errorMessage}>
        {React.createElement(childComponent, { ...props, ...loadedProps, queryForm })}
      </DataLoader>
    )
  }

}

export default StateDataLoader
