import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { withRouter } from 'react-router-dom'
import { Search } from 'semantic-ui-react'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

const AwesomebarSearch = styled(({ asFormInput, ...props }) => <Search {...props} />)`
  width: ${props => props.inputwidth || '100%'};
  ${props => (props.inputwidth ? 'display: inline-block;' : '')}
  
  ${props => (props.asFormInput ? `
    .input {
      max-width: none !important;
      padding: 0 !important;
       
      input {
        padding: 0.67857143em 1em !important;
        margin: 0 !important;
      }
    }
  ` : '')}
  
  .results {
    min-width: ${props => props.inputwidth || '100%'};
    width: ${props => (props.inputwidth ? 'fit-content' : '100%')} !important;
  }
`

class AwesomeBar extends React.PureComponent
{
  static propTypes = {
    categories: PropTypes.array,
    newWindow: PropTypes.bool,
    placeholder: PropTypes.string,
    history: PropTypes.object,
    inputwidth: PropTypes.string,
    getResultHref: PropTypes.func,
    onResultSelect: PropTypes.func,
    asFormInput: PropTypes.bool,
  }

  constructor(props) {
    super(props)

    this.state = {}

    this.httpRequestHelper = new HttpRequestHelper(
      '/api/awesomebar',
      this.handleHttpSuccess,
      this.handleHttpError,
    )
  }

  componentWillMount() {
    this.resetComponent()
  }

  render() {
    return <AwesomebarSearch
      category
      selectFirstResult
      inputwidth={this.props.inputwidth}
      loading={this.state.isLoading}
      onResultSelect={this.handleResultSelect}
      onSearchChange={this.handleSearchChange}
      results={this.state.results}
      value={this.state.value}
      minCharacters={1}
      placeholder={this.props.placeholder || 'Search project, family, gene name, etc.'}
      asFormInput={this.props.asFormInput}
    />
  }

  handleHttpSuccess = (response, urlParams) => {
    if (urlParams.q === this.state.value) {
      this.setState({ isLoading: false, results: response.matches })
    }
  }

  handleHttpError = (response) => {
    this.setState({ isLoading: false })
    console.error(response)
  }

  resetComponent = () => {
    this.setState({ isLoading: false, results: {}, value: '' })
  }

  handleSearchChange = (e, obj) => {
    this.setState({ isLoading: true, value: obj.value })
    const query = { q: obj.value }
    if (this.props.categories) {
      query.categories = this.props.categories
    }
    this.httpRequestHelper.get(query)
  }

  handleResultSelect = (e, obj) => {
    e.preventDefault()
    this.setState({ value: obj.result.title })
    const href = this.props.getResultHref ? this.props.getResultHref(obj.result) : obj.result.href
    if (this.props.onResultSelect) {
      this.props.onResultSelect(obj.result)
    } else if (this.props.newWindow) {
      window.open(href, '_blank')
    } else {
      this.props.history.push(href)
    }
  }
}

export { AwesomeBar as AwesomeBarComponent }

export const AwesomeBarFormInput = React.memo(({ onChange, parseResultItem = result => result.key, ...props }) =>
  <AwesomeBar onResultSelect={result => onChange(parseResultItem(result))} asFormInput {...props} />,
)

AwesomeBarFormInput.propTypes = {
  onChange: PropTypes.func,
  parseResultItem: PropTypes.func,
}


export default withRouter(AwesomeBar)

