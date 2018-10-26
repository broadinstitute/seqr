import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid } from 'semantic-ui-react'
import hash from 'object-hash'

import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { QueryParamsEditor } from 'shared/components/QueryParamEditor'
import VariantSearchForm from './components/VariantSearchForm'
import VariantSearchResults from './components/VariantSearchResults'
import { loadSearchedVariants } from './reducers'
import { getCurrentSearchParams } from './selectors'


const BaseVariantSearch = ({ queryParams, updateQueryParams, searchParams, search }) => {

  const onSubmit = (updatedSearchParams) => {
    const searchHash = hash.MD5(updatedSearchParams)
    search(searchHash, updatedSearchParams)
    updateQueryParams({ ...queryParams, search: searchHash })
  }

  // TODO initial project or analysisGroup
  const initialValues = searchParams || queryParams
  initialValues.familyContext = initialValues.familyContext ||
    (initialValues.familyGuid ? [{ familyGuids: [initialValues.familyGuid] }] : [])

  return (
    <Grid>
      <Grid.Row>
        <Grid.Column width={16}>
          <ReduxFormWrapper
            initialValues={initialValues}
            onSubmit={onSubmit}
            form="variantSearch"
            submitButtonText="Search"
            noModal
            renderChildren={VariantSearchForm}
          />
        </Grid.Column>
      </Grid.Row>
      <VariantSearchResults queryParams={queryParams} updateQueryParams={updateQueryParams} />
    </Grid>
  )
}

BaseVariantSearch.propTypes = {
  queryParams: PropTypes.object,
  updateQueryParams: PropTypes.func,
  searchParams: PropTypes.object,
  search: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  searchParams: getCurrentSearchParams(state, ownProps),
})

const mapDispatchToProps = {
  search: loadSearchedVariants,
}

const VariantSearch = connect(mapStateToProps, mapDispatchToProps)(BaseVariantSearch)

export default props => <QueryParamsEditor {...props}><VariantSearch /></QueryParamsEditor>
