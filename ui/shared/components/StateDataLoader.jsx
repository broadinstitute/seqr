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
    query: PropTypes.object,
  }

  state = {
    loadedProps: null,
    loading: false,
    errorHeader: null,
    error: null,
    query: {},
  }

  componentDidUpdate(prevProps, prevState) {
    const { url, query: propsQuery } = this.props
    const { query } = this.state
    if (prevProps.url !== url || prevProps.query !== propsQuery || prevState.query !== query) {
      this.load()
    }
  }

  load = () => {
    const {
      url, errorHeader, validationErrorHeader, validationErrorMessage, parseResponse, validateResponse,
      query: propsQuery,
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
        const updates = { loading: false, error: false, loadedProps }
        if (validateResponse && !validateResponse(loadedProps)) {
          updates.errorHeader = validationErrorHeader
          updates.error = validationErrorMessage
        }
        this.setState(updates)
      },
      (e) => {
        this.setState({ loading: false, errorHeader, error: e.message })
      }).get(propsQuery || query)
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
