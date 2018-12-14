import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Message } from 'semantic-ui-react'
import styled from 'styled-components'

import DataLoader from 'shared/components/DataLoader'
import { HorizontalSpacer } from 'shared/components/Spacers'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import Variants from 'shared/components/panel/variants/Variants'
import { VARIANT_SORT_FIELD_NO_FAMILY_SORT, VARIANT_PAGINATION_FIELD } from 'shared/utils/constants'

import { searchVariants } from '../reducers'
import {
  getSearchedVariants,
  getSearchedVariantsIsLoading,
  getSearchedVariantsErrorMessage,
  getTotalVariantsCount,
  getVariantSearchDisplay,
  getSearchedVariantExportConfig,
} from '../selectors'


const LargeRow = styled(Grid.Row)`
  font-size: 1.15em;
  
  label {
    font-size: 1em !important;
  }
`

const FIELDS = [
  VARIANT_SORT_FIELD_NO_FAMILY_SORT,
]


const VariantSearchResults = ({
  searchedVariants, variantSearchDisplay, searchedVariantExportConfig, queryParams,
  loading, load, errorMessage, onSubmit, totalVariantsCount,
}) => {
  const { page = 1, recordsPerPage } = variantSearchDisplay
  const variantDisplayPageOffset = (page - 1) * recordsPerPage
  const fields = totalVariantsCount > recordsPerPage ?
    [...FIELDS, { ...VARIANT_PAGINATION_FIELD, totalPages: Math.ceil(totalVariantsCount / recordsPerPage) }]
    : FIELDS

  return (
    <DataLoader
      contentId={queryParams.search}
      content={searchedVariants}
      loading={loading}
      load={load}
      errorMessage={errorMessage &&
        <Grid.Row>
          <Grid.Column width={16}>
            <Message error content={errorMessage} />
          </Grid.Column>
        </Grid.Row>
      }
    >
      {queryParams.search &&
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

VariantSearchResults.propTypes = {
  load: PropTypes.func,
  searchedVariants: PropTypes.array,
  loading: PropTypes.bool,
  errorMessage: PropTypes.string,
  variantSearchDisplay: PropTypes.object,
  onSubmit: PropTypes.func,
  searchedVariantExportConfig: PropTypes.array,
  totalVariantsCount: PropTypes.number,
  queryParams: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  searchedVariants: getSearchedVariants(state),
  loading: getSearchedVariantsIsLoading(state),
  variantSearchDisplay: getVariantSearchDisplay(state),
  searchedVariantExportConfig: getSearchedVariantExportConfig(state),
  totalVariantsCount: getTotalVariantsCount(state, ownProps),
  errorMessage: getSearchedVariantsErrorMessage(state),
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    load: (searchHash) => {
      const { sort, page } = ownProps.queryParams
      dispatch(searchVariants({
        searchHash,
        displayUpdates: { sort, page },
        updateQueryParams: ownProps.updateQueryParams,
      }))
    },
    onSubmit: (updates) => {
      dispatch(searchVariants({
        searchHash: ownProps.queryParams.search,
        displayUpdates: updates,
        updateQueryParams: ownProps.updateQueryParams,
      }))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(VariantSearchResults)
