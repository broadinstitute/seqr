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

class AwesomeBar extends React.PureComponent {

  static propTypes = {
    categories: PropTypes.arrayOf(PropTypes.string),
    newWindow: PropTypes.bool,
    placeholder: PropTypes.string,
    history: PropTypes.object,
    inputwidth: PropTypes.string,
    getResultHref: PropTypes.func,
    onResultSelect: PropTypes.func,
    asFormInput: PropTypes.bool,
    parseResultItem: PropTypes.func,
  }

  state = {}

  componentDidMount() {
    this.resetComponent()
  }

  handleHttpSuccess = (response, urlParams) => {
    const { value } = this.state
    if (urlParams.q === value) {
      this.setState({ isLoading: false, results: response.matches })
    }
  }

  handleHttpError = () => {
    this.setState({ isLoading: false })
  }

  resetComponent = () => {
    this.setState({ isLoading: false, results: {}, value: '' })
  }

  handleSearchChange = (e, obj) => {
    const { categories } = this.props
    this.setState({ isLoading: true, value: obj.value })
    const query = { q: obj.value }
    if (categories) {
      query.categories = categories
    }
    new HttpRequestHelper(
      '/api/awesomebar',
      this.handleHttpSuccess,
      this.handleHttpError,
    ).get(query)
  }

  handleResultSelect = (e, obj) => {
    const { getResultHref, onResultSelect, parseResultItem, newWindow, history } = this.props
    e.preventDefault()
    this.setState({ value: obj.result.title })
    const href = getResultHref ? getResultHref(obj.result) : obj.result.href
    if (onResultSelect) {
      const result = parseResultItem ? parseResultItem(obj.result) : obj.result
      onResultSelect(result)
    } else if (newWindow) {
      window.open(href, '_blank')
    } else {
      history.push(href)
    }
  }

  render() {
    const { inputwidth, placeholder, asFormInput } = this.props
    const { isLoading, results, value } = this.state
    return (
      <AwesomebarSearch
        category
        selectFirstResult
        inputwidth={inputwidth}
        loading={isLoading}
        onResultSelect={this.handleResultSelect}
        onSearchChange={this.handleSearchChange}
        results={results}
        value={value}
        minCharacters={1}
        placeholder={placeholder || 'Search project, family, gene name, etc.'}
        asFormInput={asFormInput}
      />
    )
  }

}

export { AwesomeBar as AwesomeBarComponent }

const defaultParseResultItem = result => result.key

export const AwesomeBarFormInput = React.memo(({ onChange, parseResultItem = defaultParseResultItem, ...props }) => (
  <AwesomeBar onResultSelect={onChange} parseResultItem={parseResultItem} asFormInput {...props} />
))

AwesomeBarFormInput.propTypes = {
  onChange: PropTypes.func,
  parseResultItem: PropTypes.func,
}

export default withRouter(AwesomeBar)
