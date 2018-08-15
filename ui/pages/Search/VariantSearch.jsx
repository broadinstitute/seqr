import React from 'react'
import PropTypes from 'prop-types'
import queryString from 'query-string'
import { connect } from 'react-redux'

import { loadSearchedVariants } from 'redux/rootReducer'
import { getSearchedVariants, getSearchedVariantsIsLoading, getSavedVariantsByGuid } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import Variants from 'shared/components/panel/variants/Variants'


const VariantSearch = ({ searchedVariants, savedVariantsByGuid, location, loading, load }) => {
  const variants = searchedVariants.map(
    variant => (variant.variantGuid ? savedVariantsByGuid[variant.variantGuid] : variant),
  )
  return (
    <DataLoader contentId={queryString.parse(location.search)} content={variants.length > 0 && variants} loading={loading} load={load}>
      <Variants variants={variants} />
    </DataLoader>
  )
}

VariantSearch.propTypes = {
  load: PropTypes.func.isRequired,
  searchedVariants: PropTypes.array,
  savedVariantsByGuid: PropTypes.object,
  loading: PropTypes.bool,
  location: PropTypes.object,
}

const mapStateToProps = state => ({
  searchedVariants: getSearchedVariants(state),
  loading: getSearchedVariantsIsLoading(state),
  savedVariantsByGuid: getSavedVariantsByGuid(state),
})

const mapDispatchToProps = {
  load: loadSearchedVariants,
}

export default connect(mapStateToProps, mapDispatchToProps)(VariantSearch)
