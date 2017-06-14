import React from 'react'
import PropTypes from 'prop-types'

import { Search } from 'semantic-ui-react'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { connect } from 'react-redux'

class AwesomeBar extends React.Component
{
  static propTypes = {}

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
    return <Search
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
    console.log('received', response.matches)
    this.setState({ isLoading: false, results: response.matches })
  }

  handleHttpError = (response) => {
    this.setState({ isLoading: false })
    console.error(response)
  }

  resetComponent = () => {
    this.setState({ isLoading: false, results: {}, value: '' })
  }

  handleSearchChange = (e, value) => {
    this.setState({ isLoading: true, value })
    this.httpRequestHelper.get({
      q: value,
      proj: this.props.reduxState && this.props.reduxState.project ? this.props.reduxState.project.projectGuid : null,
    })
  }

  handleResultSelect = (e, result) => {
    e.preventDefault()
    this.setState({ value: result.title })
    window.open(result.href, '_blank')
  }
}

AwesomeBar.propTypes = {
  reduxState: PropTypes.object,
}

export { AwesomeBar as AwesomeBarComponent }


// wrap top-level component so that redux state is passed in as props
const mapStateToProps = state => ({
  reduxState: state,
})

export default connect(mapStateToProps)(AwesomeBar)

