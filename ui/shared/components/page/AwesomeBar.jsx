import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { withRouter } from 'react-router-dom'
import { Search } from 'semantic-ui-react'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

const AwesomebarSearch = styled(Search)`
  min-width: 350px;
  
  .ui.icon.input {
    max-width: 100%;
  }
`

class AwesomeBar extends React.Component
{
  static propTypes = {
    categories: PropTypes.array,
    newWindow: PropTypes.bool,
    history: PropTypes.object,
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
      fluid
      category
      selectFirstResult
      loading={this.state.isLoading}
      onResultSelect={this.handleResultSelect}
      onSearchChange={this.handleSearchChange}
      results={this.state.results}
      value={this.state.value}
      minCharacters={1}
      placeholder="Search project, family, gene name, etc."
    />
  }

  handleHttpSuccess = (response) => {
    this.setState({ isLoading: false, results: response.matches })
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
    this.httpRequestHelper.get({
      q: obj.value,
      categories: this.props.categories || '',
    })
  }

  handleResultSelect = (e, obj) => {
    e.preventDefault()
    this.setState({ value: obj.result.title })
    if (this.props.newWindow) {
      window.open(obj.result.href, '_blank')
    } else {
      this.props.history.push(obj.result.href)
    }
  }
}

export { AwesomeBar as AwesomeBarComponent }


export default withRouter(AwesomeBar)

