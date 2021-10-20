import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Grid, Dropdown, Message } from 'semantic-ui-react'
import styled from 'styled-components'

import { getSavedVariantsIsLoading, getSavedVariantsLoadingError } from 'redux/selectors'
import {
  DISCOVERY_CATEGORY_NAME,
  VARIANT_PAGINATION_FIELD,
} from 'shared/utils/constants'

import ExportTableButton from '../../buttons/ExportTableButton'
import StateChangeForm from '../../form/StateChangeForm'
import { HorizontalSpacer } from '../../Spacers'
import DataLoader from '../../DataLoader'
import Variants from './Variants'
import {
  getPairedSelectedSavedVariants, getPairedFilteredSavedVariants, getSavedVariantTableState,
  getSavedVariantVisibleIndices, getSavedVariantTotalPages, getSavedVariantExportConfig,
  getVisibleSortedSavedVariants,
} from './selectors'

const ALL_FILTER = 'ALL'

const ControlsRow = styled(Grid.Row)`
  font-size: 1.1em;
  
  label {
    font-size: 1.1em !important;
  }
  
  .pagination {
    margin-top: 10px !important;
  }
`

class SavedVariants extends React.PureComponent {

  static propTypes = {
    match: PropTypes.object,
    history: PropTypes.object,
    tagOptions: PropTypes.arrayOf(PropTypes.object),
    filters: PropTypes.arrayOf(PropTypes.object),
    discoveryFilters: PropTypes.arrayOf(PropTypes.object),
    loading: PropTypes.bool,
    error: PropTypes.string,
    variantsToDisplay: PropTypes.arrayOf(PropTypes.object),
    totalVariantsCount: PropTypes.number,
    filteredVariantsCount: PropTypes.number,
    variantExportConfig: PropTypes.arrayOf(PropTypes.object),
    tableState: PropTypes.object,
    firstRecordIndex: PropTypes.number,
    totalPages: PropTypes.number,
    updateTableField: PropTypes.func,
    getUpdateTagUrl: PropTypes.func,
    loadVariants: PropTypes.func,
    additionalFilter: PropTypes.node,
    tableSummaryComponent: PropTypes.elementType,
  }

  navigateToTag = (e, data) => {
    const { history, getUpdateTagUrl } = this.props
    history.push(getUpdateTagUrl(data.value))
  }

  render() {
    const {
      match, tableState, filters, discoveryFilters, totalPages, variantsToDisplay, totalVariantsCount, firstRecordIndex,
      tableSummaryComponent, loading, filteredVariantsCount, tagOptions, additionalFilter, updateTableField,
      variantExportConfig, loadVariants, error,
    } = this.props
    const { familyGuid, variantGuid, tag } = match.params

    const appliedTagCategoryFilter = tag || (variantGuid ? null : (tableState.categoryFilter || ALL_FILTER))

    let allFilters = (discoveryFilters && appliedTagCategoryFilter === DISCOVERY_CATEGORY_NAME) ?
      discoveryFilters : filters
    if (totalPages > 1) {
      allFilters = allFilters.concat({ ...VARIANT_PAGINATION_FIELD, totalPages })
    }

    const allShown = variantsToDisplay.length === totalVariantsCount
    let shownSummary = ''
    if (!allShown) {
      shownSummary = `${variantsToDisplay.length > 0 ? firstRecordIndex + 1 : 0}-${firstRecordIndex + variantsToDisplay.length} of`
    }

    return (
      <Grid stackable>
        {tableSummaryComponent && React.createElement(tableSummaryComponent, {
          familyGuid: variantGuid ? ((variantsToDisplay[0] || {}).familyGuids || [])[0] : familyGuid,
          ...tableState,
        })}
        {!loading && (
          <ControlsRow>
            <Grid.Column width={4}>
              {`Showing ${shownSummary} ${filteredVariantsCount}  `}
              <Dropdown
                inline
                options={tagOptions}
                value={appliedTagCategoryFilter}
                onChange={this.navigateToTag}
              />
              {` variants ${allShown ? '' : `(${totalVariantsCount} total)`}`}

            </Grid.Column>
            <Grid.Column width={12} floated="right" textAlign="right">
              {additionalFilter}
              {!variantGuid && (
                <StateChangeForm
                  updateField={updateTableField}
                  initialValues={tableState}
                  fields={allFilters}
                />
              )}
              <HorizontalSpacer width={10} />
              <ExportTableButton downloads={variantExportConfig} />
            </Grid.Column>
          </ControlsRow>
        )}
        <Grid.Row>
          <Grid.Column width={16}>
            <DataLoader
              load={loadVariants}
              contentId={match.params}
              reloadOnIdUpdate
              loading={loading}
              errorMessage={error && <Message error content={error} />}
              content={variantsToDisplay}
            >
              <Variants variants={variantsToDisplay} />
            </DataLoader>
          </Grid.Column>
        </Grid.Row>
      </Grid>
    )
  }

}

const mapStateToProps = (state, ownProps) => ({
  loading: getSavedVariantsIsLoading(state),
  error: getSavedVariantsLoadingError(state),
  variantsToDisplay: getVisibleSortedSavedVariants(state, ownProps),
  totalVariantsCount: getPairedSelectedSavedVariants(state, ownProps).length,
  filteredVariantsCount: getPairedFilteredSavedVariants(state, ownProps).length,
  tableState: getSavedVariantTableState(state, ownProps),
  firstRecordIndex: getSavedVariantVisibleIndices(state, ownProps)[0],
  totalPages: getSavedVariantTotalPages(state, ownProps),
  variantExportConfig: getSavedVariantExportConfig(state, ownProps),
})

export default connect(mapStateToProps)(SavedVariants)
