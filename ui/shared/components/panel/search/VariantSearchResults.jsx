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
import { VARIANT_SEARCH_SORT_FIELD, VARIANT_PAGINATION_FIELD } from '../../../utils/constants'
import DataLoader from '../../DataLoader'
import { QueryParamsEditor } from '../../QueryParamEditor'
import { HorizontalSpacer } from '../../Spacers'
import ExportTableButton from '../../buttons/ExportTableButton'
import ReduxFormWrapper from '../../form/ReduxFormWrapper'
import Variants from '../variants/Variants'
import GeneBreakdown from './GeneBreakdown'

const LargeRow = styled(Grid.Row)`
  font-size: 1.15em;

  label {
    font-size: 1em !important;
  }
`

const scrollToTop = () => window.scrollTo(0, 0)

const FIELDS = [
  VARIANT_SEARCH_SORT_FIELD,
]

export const DisplayVariants = React.memo(({ displayVariants }) =>
  <Grid.Row>
    <Grid.Column width={16}>
      <Variants variants={displayVariants} linkToSavedVariants />
    </Grid.Column>
  </Grid.Row>,
)

DisplayVariants.propTypes = {
  displayVariants: PropTypes.array,
}

const BaseVariantSearchResultsContent = React.memo((
  { match, variantSearchDisplay, searchedVariantExportConfig, onSubmit, totalVariantsCount, additionalDisplayEdit, displayVariants }) => {
  const { searchHash } = match.params
  const { page = 1, recordsPerPage } = variantSearchDisplay
  const variantDisplayPageOffset = (page - 1) * recordsPerPage
  const paginationFields = totalVariantsCount > recordsPerPage ? [{ ...VARIANT_PAGINATION_FIELD, totalPages: Math.ceil(totalVariantsCount / recordsPerPage) }] : []
  const fields = [...FIELDS, ...paginationFields]

  return [
    <LargeRow key="resultsSummary">
      <Grid.Column width={5}>
        {totalVariantsCount === displayVariants.length ? 'Found ' : `Showing ${variantDisplayPageOffset + 1}-${variantDisplayPageOffset + displayVariants.length} of `}
        <b>{totalVariantsCount}</b> variants
      </Grid.Column>
      <Grid.Column width={11} floated="right" textAlign="right">
        {additionalDisplayEdit}
        <ReduxFormWrapper
          onSubmit={onSubmit}
          form="editSearchedVariantsDisplayTop"
          initialValues={variantSearchDisplay}
          closeOnSuccess={false}
          submitOnChange
          inline
          fields={fields}
        />
        <HorizontalSpacer width={10} />
        <ExportTableButton downloads={searchedVariantExportConfig} buttonText="Download" />
        <HorizontalSpacer width={10} />
        <GeneBreakdown searchHash={searchHash} />
      </Grid.Column>
    </LargeRow>,
    <DisplayVariants key="variants" displayVariants={displayVariants} />,
    <LargeRow key="bottomPagination">
      <Grid.Column width={11} floated="right" textAlign="right">
        <ReduxFormWrapper
          onSubmit={onSubmit}
          form="editSearchedVariantsDisplayBottom"
          initialValues={variantSearchDisplay}
          closeOnSuccess={false}
          submitOnChange
          inline
          fields={paginationFields}
        />
        <HorizontalSpacer width={10} />
        <Button onClick={scrollToTop}>Scroll To Top</Button>
        <HorizontalSpacer width={10} />
      </Grid.Column>
    </LargeRow>,
  ]
})

BaseVariantSearchResultsContent.propTypes = {
  match: PropTypes.object,
  onSubmit: PropTypes.func,
  variantSearchDisplay: PropTypes.object,
  searchedVariantExportConfig: PropTypes.array,
  totalVariantsCount: PropTypes.number,
  displayVariants: PropTypes.array,
  additionalDisplayEdit: PropTypes.node,
}

const mapContentStateToProps = (state, ownProps) => ({
  variantsLoading: getSearchedVariantsIsLoading(state),
  variantSearchDisplay: getVariantSearchDisplay(state),
  searchedVariantExportConfig: getSearchedVariantExportConfig(state, ownProps),
  totalVariantsCount: getTotalVariantsCount(state, ownProps),
  errorMessage: getSearchedVariantsErrorMessage(state),
})

const mapContentDispatchToProps = (dispatch, ownProps) => {
  return {
    onSubmit: (updates) => {
      dispatch(loadSearchedVariants(ownProps.match.params, {
        displayUpdates: updates,
        ...ownProps,
      }))
    },
  }
}

const VariantSearchResultsContent = connect(mapContentStateToProps, mapContentDispatchToProps)(BaseVariantSearchResultsContent)

const BaseVariantSearchResults = React.memo((
  { match, displayVariants, load, unload, initialLoad, variantsLoading, contextLoading, errorMessage, contentComponent, ...props }) => {
  return (
    <DataLoader
      contentId={match.params}
      content={displayVariants}
      loading={variantsLoading || contextLoading}
      load={load}
      unload={unload}
      initialLoad={initialLoad}
      reloadOnIdUpdate
      errorMessage={errorMessage &&
        <Grid.Row>
          <Grid.Column width={16}>
            <Message error content={errorMessage} />
          </Grid.Column>
        </Grid.Row>
      }
    >
      {React.createElement(contentComponent || VariantSearchResultsContent, { match, displayVariants, ...props })}
    </DataLoader>
  )
})

BaseVariantSearchResults.propTypes = {
  match: PropTypes.object,
  load: PropTypes.func,
  unload: PropTypes.func,
  initialLoad: PropTypes.func,
  variantsLoading: PropTypes.bool,
  contextLoading: PropTypes.bool,
  errorMessage: PropTypes.string,
  displayVariants: PropTypes.array,
  contentComponent: PropTypes.elementType,
}

const mapStateToProps = (state, ownProps) => ({
  variantsLoading: getSearchedVariantsIsLoading(state),
  errorMessage: getSearchedVariantsErrorMessage(state),
  displayVariants: getDisplayVariants(state, ownProps),
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    load: (params) => {
      dispatch((ownProps.loadVariants || loadSearchedVariants)(params, ownProps))
    },
    unload: () => {
      dispatch(unloadSearchResults())
    },
  }
}

const VariantSearchResults = connect(mapStateToProps, mapDispatchToProps)(BaseVariantSearchResults)

const LoadedVariantSearchResults = React.memo(({ contentComponent, flattenCompoundHet, ...props }) => (
  <QueryParamsEditor {...props}>
    <VariantSearchResults contentComponent={contentComponent} flattenCompoundHet={flattenCompoundHet} />
  </QueryParamsEditor>
))

LoadedVariantSearchResults.propTypes = {
  contentComponent: PropTypes.node,
  flattenCompoundHet: PropTypes.bool,
}

export default LoadedVariantSearchResults

