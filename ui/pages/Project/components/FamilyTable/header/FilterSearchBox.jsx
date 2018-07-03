import React from 'react'
import PropTypes from 'prop-types'
import { Input } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { indexAndSearch } from 'redux/utils/reduxSearchEnhancer'
import QueryParamEditor from 'shared/components/QueryParamEditor'

class BaseFilterSearchBox extends React.PureComponent {
  static propTypes = {
    currentQueryParam: PropTypes.string,
    updateQueryParam: PropTypes.func,
    searchFamilies: PropTypes.func,
  }

  updateQuery = (e, data) => {
    this.props.updateQueryParam(data.value)
    this.props.searchFamilies(data.value)
  }


  componentDidMount() {
    this.props.searchFamilies(this.props.currentQueryParam)
  }

  render() {
    return <Input placeholder="Search..." onChange={this.updateQuery} defaultValue={this.props.currentQueryParam} />
  }
}

const mapDispatchToProps = {
  searchFamilies: indexAndSearch('familiesByGuid'),
}

const FilterSearchBox = connect(null, mapDispatchToProps)(BaseFilterSearchBox)

export default () =>
  <QueryParamEditor queryParam="familyFilter">
    <FilterSearchBox />
  </QueryParamEditor>
