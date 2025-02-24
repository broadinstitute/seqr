import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Message, Button } from 'semantic-ui-react'
import styled from 'styled-components'

import { loadSearchedVariants, unloadSearchResults } from 'redux/rootReducer'
import {
  getDisplayVariants,
  getSearchedVariantsIsLoading,
  getSearchedVariantsErrorMessage,
  getTotalVariantsCount,
  getVariantSearchDisplay,
  getSearchedVariantExportConfig,
} from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import { QueryParamsEditor } from 'shared/components/QueryParamEditor'
import { HorizontalSpacer } from 'shared/components/Spacers'
import ExportTableButton from 'shared/components/buttons/ExportTableButton'
import Variants from 'shared/components/panel/variants/Variants'
import GeneBreakdown from './GeneBreakdown'
import SearchDisplayForm from './SearchDisplayForm'

const LargeRow = styled(Grid.Row)`
  font-size: 1.15em;

  label {
    font-size: 1em !important;
  }
`

const scrollToTop = () => window.scrollTo(0, 0)

const DisplayVariants = React.memo(({ displayVariants, compoundHetToggle }) => (
  <Grid.Row>
    <Grid.Column width={16}>
      <Variants variants={displayVariants} compoundHetToggle={compoundHetToggle} linkToSavedVariants />
    </Grid.Column>
  </Grid.Row>
))

DisplayVariants.propTypes = {
  displayVariants: PropTypes.arrayOf(PropTypes.object),
  compoundHetToggle: PropTypes.func,
}

const BaseVariantSearchResultsContent = React.memo(({
  match, variantSearchDisplay, searchedVariantExportConfig, totalVariantsCount, additionalDisplayEdit,
  displayVariants, compoundHetToggle, ...props
}) => {
  const { searchHash } = match.params
  const { page = 1, recordsPerPage } = variantSearchDisplay
  const variantDisplayPageOffset = (page - 1) * recordsPerPage

  return [
    <LargeRow key="resultsSummary">
      <Grid.Column width={5}>
        {totalVariantsCount === displayVariants.length ? 'Found ' : `Showing ${variantDisplayPageOffset + 1}-${variantDisplayPageOffset + displayVariants.length} of `}
        <b>{totalVariantsCount}</b>
        &nbsp; variants
      </Grid.Column>
      <Grid.Column width={11} floated="right" textAlign="right">
        {additionalDisplayEdit}
        <SearchDisplayForm formLocation="Top" match={match} searchOnSubmit {...props} />
        <HorizontalSpacer width={10} />
        {searchedVariantExportConfig && <ExportTableButton downloads={searchedVariantExportConfig} buttonText="Download" disabled={totalVariantsCount > 1000} />}
        <HorizontalSpacer width={10} />
        <GeneBreakdown searchHash={searchHash} />
      </Grid.Column>
    </LargeRow>,
    <DisplayVariants key="variants" displayVariants={displayVariants} compoundHetToggle={compoundHetToggle} />,
    <LargeRow key="bottomPagination">
      <Grid.Column width={11} floated="right" textAlign="right">
        <SearchDisplayForm formLocation="Bottom" match={match} paginationOnly searchOnSubmit {...props} />
        <HorizontalSpacer width={10} />
        <Button onClick={scrollToTop}>Scroll To Top</Button>
        <HorizontalSpacer width={10} />
      </Grid.Column>
    </LargeRow>,
  ]
})

BaseVariantSearchResultsContent.propTypes = {
  match: PropTypes.object,
  variantSearchDisplay: PropTypes.object,
  searchedVariantExportConfig: PropTypes.arrayOf(PropTypes.object),
  totalVariantsCount: PropTypes.number,
  displayVariants: PropTypes.arrayOf(PropTypes.object),
  additionalDisplayEdit: PropTypes.node,
  compoundHetToggle: PropTypes.func,
}

const mapContentStateToProps = (state, ownProps) => ({
  variantsLoading: getSearchedVariantsIsLoading(state),
  variantSearchDisplay: getVariantSearchDisplay(state),
  searchedVariantExportConfig: getSearchedVariantExportConfig(state, ownProps),
  totalVariantsCount: getTotalVariantsCount(state, ownProps),
  errorMessage: getSearchedVariantsErrorMessage(state),
})

const VariantSearchResultsContent = connect(mapContentStateToProps)(BaseVariantSearchResultsContent)

const ErrorResults = ({ errorMessage, match }) => ([
  <Grid.Row key="sort">
    <Grid.Column width={16} floated="right" textAlign="right">
      <SearchDisplayForm formLocation="Error" match={match} />
    </Grid.Column>
  </Grid.Row>,
  <Grid.Row key="error">
    <Grid.Column width={16}>
      <Message error content={errorMessage} />
    </Grid.Column>
  </Grid.Row>,
])

ErrorResults.propTypes = {
  errorMessage: PropTypes.string,
  match: PropTypes.object,
}

const BaseVariantSearchResults = React.memo(({
  match, displayVariants, load, unload, initialLoad, variantsLoading, contextLoading, errorMessage,
  ...props
}) => (
  <DataLoader
    contentId={match.params}
    content={displayVariants}
    loading={variantsLoading || contextLoading}
    load={load}
    unload={unload}
    initialLoad={initialLoad}
    reloadOnIdUpdate
    errorMessage={errorMessage && <ErrorResults errorMessage={errorMessage} match={match} />}
  >
    {React.createElement(
      match.params.variantId ? DisplayVariants : VariantSearchResultsContent,
      { match, displayVariants, ...props },
    )}
  </DataLoader>
))

BaseVariantSearchResults.propTypes = {
  match: PropTypes.object,
  load: PropTypes.func,
  unload: PropTypes.func,
  initialLoad: PropTypes.func,
  variantsLoading: PropTypes.bool,
  contextLoading: PropTypes.bool,
  errorMessage: PropTypes.string,
  displayVariants: PropTypes.arrayOf(PropTypes.object),
}

const mapStateToProps = (state, ownProps) => ({
  variantsLoading: getSearchedVariantsIsLoading(state),
  errorMessage: getSearchedVariantsErrorMessage(state),
  displayVariants: getDisplayVariants(state, ownProps),
})

const mapDispatchToProps = (dispatch, ownProps) => ({
  load: (params) => {
    dispatch((ownProps.loadVariants || loadSearchedVariants)(params, ownProps))
  },
  unload: () => {
    dispatch(unloadSearchResults())
  },
})

const VariantSearchResults = connect(mapStateToProps, mapDispatchToProps)(BaseVariantSearchResults)

const LoadedVariantSearchResults = React.memo((
  { flattenCompoundHet, compoundHetToggle, ...props },
) => (
  <QueryParamsEditor {...props}>
    <VariantSearchResults
      flattenCompoundHet={flattenCompoundHet}
      compoundHetToggle={compoundHetToggle}
    />
  </QueryParamsEditor>
))

LoadedVariantSearchResults.propTypes = {
  flattenCompoundHet: PropTypes.bool,
  compoundHetToggle: PropTypes.func,
}

export default LoadedVariantSearchResults
