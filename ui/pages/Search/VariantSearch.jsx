import React from 'react'
import PropTypes from 'prop-types'
import queryString from 'query-string'
import { connect } from 'react-redux'

import { loadSearchedVariants } from 'redux/rootReducer'
import { getSearchedVariants, getSavedVariantsByGuid } from 'redux/selectors'
import Variants from 'shared/components/panel/variants/Variants'


class VariantSearch extends React.PureComponent {
  static propTypes = {
    loadSearchedVariants: PropTypes.func.isRequired,
    searchedVariants: PropTypes.array,
    savedVariantsByGuid: PropTypes.object,
    location: PropTypes.object,
  }

  constructor(props) {
    super(props)

    const query = queryString.parse(props.location.search)
    props.loadSearchedVariants(query)
  }

  render() {
    const variants = this.props.searchedVariants.map(
      variant => (variant.variantGuid ? this.props.savedVariantsByGuid[variant.variantGuid] : variant),
    )
    return (
      <Variants variants={variants} />
    )
  }
}

const mapStateToProps = state => ({
  searchedVariants: getSearchedVariants(state),
  savedVariantsByGuid: getSavedVariantsByGuid(state),
})

const mapDispatchToProps = {
  loadSearchedVariants,
}

export default connect(mapStateToProps, mapDispatchToProps)(VariantSearch)
