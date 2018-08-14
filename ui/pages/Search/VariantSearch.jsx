import React from 'react'
import PropTypes from 'prop-types'
import queryString from 'query-string'
import { connect } from 'react-redux'

import { loadSearchedVariants } from 'redux/rootReducer'
import { getSearchedVariants } from 'redux/selectors'


class VariantSearch extends React.Component {
  static propTypes = {
    loadSearchedVariants: PropTypes.func.isRequired,
    searchedVariants: PropTypes.array,
    location: PropTypes.object,
  }

  constructor(props) {
    super(props)

    const query = queryString.parse(props.location.search)
    props.loadSearchedVariants(query)
  }

  render() {
    return (
      <div>
        {this.props.searchedVariants.map(variant =>
          <div key={variant.variantId || `${variant.xpos}-${variant.ref}-${variant.alt}`}>{JSON.stringify(variant)}</div>,
        )}
      </div>
    )
  }
}

const mapStateToProps = state => ({
  searchedVariants: getSearchedVariants(state),
})

const mapDispatchToProps = {
  loadSearchedVariants,
}

export default connect(mapStateToProps, mapDispatchToProps)(VariantSearch)
