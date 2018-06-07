import React from 'react'
import PropTypes from 'prop-types'
import { Input } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { withRouter } from 'react-router'
import queryString from 'query-string'

import { indexAndSearch } from 'redux/utils/reduxSearchEnhancer'

const QUERY_PARAM = 'familyFilter'

class FilterSearchBox extends React.PureComponent {
  static propTypes = {
    location: PropTypes.object,
    history: PropTypes.object,
    searchFamilies: PropTypes.func,
  }

  updateQuery = (e, data) => {
    this.props.history.push({ ...this.props.location, search: data.value ? `?${QUERY_PARAM}=${data.value}` : null })
    this.props.searchFamilies(data.value)
  }

  currentValue() {
    return queryString.parse(this.props.location.search)[QUERY_PARAM]
  }

  componentDidMount() {
    this.props.searchFamilies(this.currentValue())
  }

  render() {
    return <Input placeholder="Search..." onChange={this.updateQuery} defaultValue={this.currentValue()} />
  }
}

const mapDispatchToProps = {
  searchFamilies: indexAndSearch('familiesByGuid'),
}

export default withRouter(connect(null, mapDispatchToProps)(FilterSearchBox))
