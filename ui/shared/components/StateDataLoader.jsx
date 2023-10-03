import React from 'react'
import PropTypes from 'prop-types'
import { Message } from 'semantic-ui-react'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import StateChangeForm from './form/StateChangeForm'
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
    query: {},
  }

  componentDidUpdate(prevProps, prevState) {
    const { url } = this.props
    const { query } = this.state
    if (prevProps.url !== url || prevState.query !== query) {
      this.load()
    }
  }

  load = () => {
    const {
      url, errorHeader, validationErrorHeader, validationErrorMessage, parseResponse, validateResponse,
    } = this.props
    const { query } = this.state
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

  updateField = name => (value) => {
    this.setState(prevState => ({ query: { ...prevState.query, [name]: value } }))
  }

  render() {
    const { loadedProps, loading, errorHeader, error, showEmpty, query } = this.state
    const {
      childComponent, url, validationErrorHeader, validationErrorMessage, parseResponse, validateResponse, queryFields,
      ...props
    } = this.props
    const errorMessage = error ? <Message visible error header={errorHeader} content={error} /> : null
    const queryForm = queryFields && (
      <StateChangeForm
        initialValues={query}
        fields={queryFields}
        updateField={this.updateField}
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
