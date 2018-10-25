import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid } from 'semantic-ui-react'
import hash from 'object-hash'

import { getFamiliesByGuid } from 'redux/selectors'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import DataLoader from 'shared/components/DataLoader'
import { QueryParamsEditor } from 'shared/components/QueryParamEditor'
import VariantSearchForm from './components/VariantSearchForm'
import VariantSearchResults from './components/VariantSearchResults'
import { loadSearchedProjectDetails, loadSearchedVariants } from './reducers'
import { getSearchedProjectIsLoading, getCurrentSearchParams } from './selectors'


const BaseVariantSearch = ({ queryParams, updateQueryParams, searchParams, family, loading, load, search }) => {

  const onSubmit = (updatedSearchParams) => {
    const searchHash = hash.MD5(updatedSearchParams)
    search(searchHash, updatedSearchParams)
    updateQueryParams({ ...queryParams, search: searchHash })
  }

  return (
    <DataLoader contentId={queryParams} content={queryParams.familyGuid ? family : true} loading={loading} load={load}>
      <Grid>
        <Grid.Row>
          <Grid.Column width={16}>
            <ReduxFormWrapper
              initialValues={searchParams || queryParams}
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
    </DataLoader>
  )
}

BaseVariantSearch.propTypes = {
  queryParams: PropTypes.object,
  updateQueryParams: PropTypes.func,
  searchParams: PropTypes.object,
  family: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
  search: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  family: getFamiliesByGuid(state)[ownProps.queryParams.familyGuid],
  searchParams: getCurrentSearchParams(state, ownProps),
  loading: getSearchedProjectIsLoading(state),
})

const mapDispatchToProps = {
  load: loadSearchedProjectDetails,
  search: loadSearchedVariants,
}

const VariantSearch = connect(mapStateToProps, mapDispatchToProps)(BaseVariantSearch)

export default props => <QueryParamsEditor {...props}><VariantSearch /></QueryParamsEditor>
