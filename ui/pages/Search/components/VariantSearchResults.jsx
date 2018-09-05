import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid } from 'semantic-ui-react'
import styled from 'styled-components'

import DataLoader from 'shared/components/DataLoader'
import { HorizontalSpacer } from 'shared/components/Spacers'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import Variants from 'shared/components/panel/variants/Variants'
import { VARIANT_SORT_FIELD, VARIANT_HIDE_EXCLUDED_FIELD } from 'shared/utils/constants'

import { loadSearchedVariants, updateVariantSearchDisplay } from '../reducers'
import {
  getSortedFilteredSearchedVariants,
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
  VARIANT_SORT_FIELD,
  VARIANT_HIDE_EXCLUDED_FIELD,
]

const VariantSearchResults = ({
  searchedVariants, variantSearchDisplay, searchedVariantExportConfig, search, loading, load, errorMessage,
  onSubmit, totalVariantsCount,
}) =>
  <DataLoader
    contentId={search}
    content={searchedVariants}
    loading={loading}
    load={load}
    errorMessage={errorMessage}
  >
    {search.search &&
      <LargeRow>
        <Grid.Column width={5}>
          Found <b>{totalVariantsCount}</b> variants
          {totalVariantsCount !== searchedVariants.length &&
          <span>&nbsp;({totalVariantsCount - searchedVariants.length} hidden)</span>
          }
        </Grid.Column>
        <Grid.Column width={11} floated="right" textAlign="right">
          <ReduxFormWrapper
            onSubmit={onSubmit}
            form="editSearchedVariantsDisplay"
            initialValues={variantSearchDisplay}
            closeOnSuccess={false}
            submitOnChange
            inline
            fields={FIELDS}
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

VariantSearchResults.propTypes = {
  load: PropTypes.func,
  searchedVariants: PropTypes.array,
  loading: PropTypes.bool,
  errorMessage: PropTypes.string,
  variantSearchDisplay: PropTypes.object,
  onSubmit: PropTypes.func,
  searchedVariantExportConfig: PropTypes.array,
  totalVariantsCount: PropTypes.number,
  search: PropTypes.object,
}

const mapStateToProps = state => ({
  searchedVariants: getSortedFilteredSearchedVariants(state),
  loading: getSearchedVariantsIsLoading(state),
  variantSearchDisplay: getVariantSearchDisplay(state),
  searchedVariantExportConfig: getSearchedVariantExportConfig(state),
  totalVariantsCount: getTotalVariantsCount(state),
  errorMessage: getSearchedVariantsErrorMessage(state),
})

const mapDispatchToProps = {
  load: loadSearchedVariants,
  onSubmit: updateVariantSearchDisplay,
}

export default connect(mapStateToProps, mapDispatchToProps)(VariantSearchResults)
