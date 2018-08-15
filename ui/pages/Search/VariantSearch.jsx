import React from 'react'
import PropTypes from 'prop-types'
import queryString from 'query-string'
import { connect } from 'react-redux'
import { Grid } from 'semantic-ui-react'

import DataLoader from 'shared/components/DataLoader'
import { HorizontalSpacer } from 'shared/components/Spacers'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import Variants from 'shared/components/panel/variants/Variants'
import { VARIANT_SORT_FIELD, VARIANT_HIDE_EXCLUDED_FIELD } from 'shared/utils/constants'

import { loadSearchedVariants, updateVariantSearchDisplay } from './reducers'
import {
  getSortedFilteredSearchedVariants,
  getSearchedVariantsIsLoading,
  getTotalVariantsCount,
  getVariantSearchDisplay,
  getSearchedVariantExportConfig,
} from './selectors'


const FIELDS = [
  VARIANT_SORT_FIELD,
  VARIANT_HIDE_EXCLUDED_FIELD,
]

const VariantSearch = ({
  searchedVariants, variantSearchDisplay, searchedVariantExportConfig, location, loading, load, onSubmit, totalVariantsCount,
}) =>
  <Grid>
    <DataLoader
      contentId={queryString.parse(location.search)}
      content={searchedVariants.length > 0 && searchedVariants}
      loading={loading}
      load={load}
    >
      <Grid.Row>
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
          <ExportTableButton downloads={searchedVariantExportConfig} />
        </Grid.Column>
      </Grid.Row>
      <Grid.Row>
        <Grid.Column width={16}>
          <Variants variants={searchedVariants} />
        </Grid.Column>
      </Grid.Row>
    </DataLoader>
  </Grid>

VariantSearch.propTypes = {
  load: PropTypes.func,
  searchedVariants: PropTypes.array,
  loading: PropTypes.bool,
  variantSearchDisplay: PropTypes.object,
  onSubmit: PropTypes.func,
  searchedVariantExportConfig: PropTypes.array,
  totalVariantsCount: PropTypes.number,
  location: PropTypes.object,
}

const mapStateToProps = state => ({
  searchedVariants: getSortedFilteredSearchedVariants(state),
  loading: getSearchedVariantsIsLoading(state),
  variantSearchDisplay: getVariantSearchDisplay(state),
  searchedVariantExportConfig: getSearchedVariantExportConfig(state),
  totalVariantsCount: getTotalVariantsCount(state),
})

const mapDispatchToProps = {
  load: loadSearchedVariants,
  onSubmit: updateVariantSearchDisplay,
}

export default connect(mapStateToProps, mapDispatchToProps)(VariantSearch)
