import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Message, Button } from 'semantic-ui-react'
import styled from 'styled-components'
import uniqBy from 'lodash/uniqBy'

import DataLoader from 'shared/components/DataLoader'
import { QueryParamsEditor } from 'shared/components/QueryParamEditor'
import { HorizontalSpacer } from 'shared/components/Spacers'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import Variants from 'shared/components/panel/variants/Variants'
import { VARIANT_SORT_FIELD_NO_FAMILY_SORT, VARIANT_PAGINATION_FIELD, FLATTEN_COMPOUND_HET_TOGGLE_FIELD } from 'shared/utils/constants'

import { loadSearchedVariants, unloadSearchResults, updateCompoundHetDisplay } from '../reducers'
import {
  getSearchedVariants,
  getSearchedVariantsIsLoading,
  getSearchedVariantsErrorMessage,
  getTotalVariantsCount,
  getVariantSearchDisplay,
  getCompoundHetDisplay,
  getFlattenedCompoundHets,
  getCompoundHetDisplayLoading,
  getSearchedVariantExportConfig,
  getSearchContextIsLoading,
  getInhertanceFilterMode,
} from '../selectors'
import GeneBreakdown from './GeneBreakdown'
import { ALL_RECESSIVE_INHERITANCE_FILTERS } from '../constants'


const LargeRow = styled(Grid.Row)`
  font-size: 1.15em;

  label {
    font-size: 1em !important;
  }
`

const scrollToTop = () => window.scrollTo(0, 0)

const FIELDS = [
  VARIANT_SORT_FIELD_NO_FAMILY_SORT,
]

const BaseVariantSearchResults = ({
  match, searchedVariants, variantSearchDisplay, searchedVariantExportConfig, onSubmit, load, unload, loading, errorMessage, totalVariantsCount, inheritanceFilter, compoundHetDisplay, toggleUnpair, flattenedCompoundHets,
}) => {
  const { searchHash, variantId } = match.params
  const { page = 1, recordsPerPage } = variantSearchDisplay
  const variantDisplayPageOffset = (page - 1) * recordsPerPage
  const paginationFields = totalVariantsCount > recordsPerPage ? [{ ...VARIANT_PAGINATION_FIELD, totalPages: Math.ceil(totalVariantsCount / recordsPerPage) }] : []
  // TODO move flatten into selector! <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
  const displayVariants = compoundHetDisplay.flattenCompoundHet ? flattenedCompoundHets : searchedVariants
  const compoundHetDisplayFields = ALL_RECESSIVE_INHERITANCE_FILTERS.includes(inheritanceFilter) ? [FLATTEN_COMPOUND_HET_TOGGLE_FIELD] : []
  const fields = [...FIELDS, ...paginationFields]
  return (
    <DataLoader
      contentId={searchHash || variantId}
      content={displayVariants}
      loading={loading}
      load={load}
      unload={unload}
      reloadOnIdUpdate
      errorMessage={errorMessage &&
        <Grid.Row>
          <Grid.Column width={16}>
            <Message error content={errorMessage} />
          </Grid.Column>
        </Grid.Row>
      }
    >
      {searchHash &&
        <LargeRow>
          <Grid.Column width={5}>
            {totalVariantsCount === displayVariants.length ? 'Found ' : `Showing ${variantDisplayPageOffset + 1}-${variantDisplayPageOffset + displayVariants.length} of `}
            <b>{totalVariantsCount + (displayVariants.length - searchedVariants.length)}</b> variants
          </Grid.Column>
          <Grid.Column width={11} floated="right" textAlign="right">
            <ReduxFormWrapper
              onSubmit={toggleUnpair}
              form="toggleUnpairCompoundHet"
              initialValues={compoundHetDisplay}
              closeOnSuccess={false}
              submitOnChange
              inline
              fields={compoundHetDisplayFields}
            />
            <HorizontalSpacer width={10} />
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
        </LargeRow>
      }
      <Grid.Row>
        <Grid.Column width={16}>
          <Variants variants={displayVariants} />
        </Grid.Column>
      </Grid.Row>
      {searchHash &&
        <LargeRow>
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
        </LargeRow>
      }
    </DataLoader>
  )
}

BaseVariantSearchResults.propTypes = {
  match: PropTypes.object,
  load: PropTypes.func,
  unload: PropTypes.func,
  onSubmit: PropTypes.func,
  searchedVariants: PropTypes.array,
  loading: PropTypes.bool,
  errorMessage: PropTypes.string,
  variantSearchDisplay: PropTypes.object,
  searchedVariantExportConfig: PropTypes.array,
  totalVariantsCount: PropTypes.number,
  inheritanceFilter: PropTypes.string,
  compoundHetDisplay: PropTypes.object,
  flattenedCompoundHets: PropTypes.array,
  toggleUnpair: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  searchedVariants: getSearchedVariants(state),
  loading: getSearchedVariantsIsLoading(state) || getSearchContextIsLoading(state),
  // loading: getSearchedVariantsIsLoading(state) || getSearchContextIsLoading(state) || getCompoundHetDisplayLoading(state),
  variantSearchDisplay: getVariantSearchDisplay(state),
  searchedVariantExportConfig: getSearchedVariantExportConfig(state, ownProps),
  totalVariantsCount: getTotalVariantsCount(state, ownProps),
  errorMessage: getSearchedVariantsErrorMessage(state),
  inheritanceFilter: getInhertanceFilterMode(state),
  compoundHetDisplay: getCompoundHetDisplay(state),
  flattenedCompoundHets: getFlattenedCompoundHets(state),
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    load: () => {
      dispatch(loadSearchedVariants({
        ...ownProps.match.params,
        ...ownProps,
      }))
    },
    onSubmit: (updates) => {
      dispatch(loadSearchedVariants({
        searchHash: ownProps.match.params.searchHash,
        displayUpdates: updates,
        ...ownProps,
      }))
    },
    unload: () => {
      dispatch(unloadSearchResults())
    },
    toggleUnpair: (updates) => {
      dispatch(updateCompoundHetDisplay({
        updates,
      }))
    },
  }
}

const VariantSearchResults = connect(mapStateToProps, mapDispatchToProps)(BaseVariantSearchResults)

export default props => <QueryParamsEditor {...props}><VariantSearchResults /></QueryParamsEditor>
