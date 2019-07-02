import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Message } from 'semantic-ui-react'
import styled from 'styled-components'

import DataLoader from 'shared/components/DataLoader'
import { QueryParamsEditor } from 'shared/components/QueryParamEditor'
import { HorizontalSpacer } from 'shared/components/Spacers'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import Variants from 'shared/components/panel/variants/Variants'
import { VARIANT_SORT_FIELD_NO_FAMILY_SORT, VARIANT_PAGINATION_FIELD } from 'shared/utils/constants'

import { loadSearchedVariants, unloadSearchResults } from '../reducers'
import {
  getSearchedVariants,
  getSearchedVariantsIsLoading,
  getSearchedVariantsErrorMessage,
  getTotalVariantsCount,
  getVariantSearchDisplay,
  getSearchedVariantExportConfig,
  getSearchContextIsLoading,
} from '../selectors'
import GeneBreakdown from './GeneBreakdown'


const LargeRow = styled(Grid.Row)`
  font-size: 1.15em;
  
  label {
    font-size: 1em !important;
  }
`

const FIELDS = [
  VARIANT_SORT_FIELD_NO_FAMILY_SORT,
]


const BaseVariantSearchResults = ({
  match, searchedVariants, variantSearchDisplay, searchedVariantExportConfig, onSubmit, load, unload, loading, errorMessage, totalVariantsCount,
}) => {
  const { searchHash, variantId } = match.params
  const { page = 1, recordsPerPage } = variantSearchDisplay
  const variantDisplayPageOffset = (page - 1) * recordsPerPage
  const fields = totalVariantsCount > recordsPerPage ?
    [...FIELDS, { ...VARIANT_PAGINATION_FIELD, totalPages: Math.ceil(totalVariantsCount / recordsPerPage) }]
    : FIELDS
  return (
    <DataLoader
      contentId={searchHash || variantId}
      content={searchedVariants}
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
            {totalVariantsCount === searchedVariants.length ? 'Found ' : `Showing ${variantDisplayPageOffset + 1}-${variantDisplayPageOffset + searchedVariants.length} of `}
            <b>{totalVariantsCount}</b> variants
          </Grid.Column>
          <Grid.Column width={11} floated="right" textAlign="right">
            <ReduxFormWrapper
              onSubmit={onSubmit}
              form="editSearchedVariantsDisplay"
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
          <Variants variants={searchedVariants} />
        </Grid.Column>
      </Grid.Row>
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
}

const mapStateToProps = (state, ownProps) => ({
  searchedVariants: getSearchedVariants(state),
  loading: getSearchedVariantsIsLoading(state) || getSearchContextIsLoading(state),
  variantSearchDisplay: getVariantSearchDisplay(state),
  searchedVariantExportConfig: getSearchedVariantExportConfig(state, ownProps),
  totalVariantsCount: getTotalVariantsCount(state, ownProps),
  errorMessage: getSearchedVariantsErrorMessage(state),
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
  }
}

const VariantSearchResults = connect(mapStateToProps, mapDispatchToProps)(BaseVariantSearchResults)

export default props => <QueryParamsEditor {...props}><VariantSearchResults /></QueryParamsEditor>
