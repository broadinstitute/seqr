import React from 'react'
import PropTypes from 'prop-types'
import { Input } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { createSearchAction } from 'redux-search'


import { indexAndSearch } from 'redux/utils/reduxSearchEnhancer'
import { getProjectFamiliesByGuid } from 'pages/Project/selectors'
import QueryParamEditor from 'shared/components/QueryParamEditor'

class BaseFilterSearchBox extends React.PureComponent {
  static propTypes = {
    currentQueryParam: PropTypes.string,
    updateQueryParam: PropTypes.func,
    searchFamilies: PropTypes.func,
    indexAndSearchFamilies: PropTypes.func,
    projectFamilies: PropTypes.object,
  }

  updateQuery = (e, data) => {
    this.props.updateQueryParam(data.value)
    this.props.searchFamilies(data.value)
  }


  componentDidMount() {
    this.props.indexAndSearchFamilies(this.props.currentQueryParam)
  }

  componentDidUpdate(prevProps) {
    if (prevProps.projectFamilies !== this.props.projectFamilies) {
      this.props.indexAndSearchFamilies(this.props.currentQueryParam)
    } else if (prevProps.currentQueryParam !== this.props.currentQueryParam) {
      this.props.searchFamilies(this.props.currentQueryParam)
    }
  }

  render() {
    return <Input placeholder="Search..." onChange={this.updateQuery} defaultValue={this.props.currentQueryParam} />
  }
}

const mapStateToProps = state => ({
  projectFamilies: getProjectFamiliesByGuid(state),
})

const mapDispatchToProps = {
  indexAndSearchFamilies: indexAndSearch('familiesByGuid'),
  searchFamilies: createSearchAction('familiesByGuid'),
}

const FilterSearchBox = connect(mapStateToProps, mapDispatchToProps)(BaseFilterSearchBox)

export default () =>
  <QueryParamEditor queryParam="familyFilter">
    <FilterSearchBox />
  </QueryParamEditor>
