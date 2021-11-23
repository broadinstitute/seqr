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
import { getPairedSelectedSavedVariants, getPairedFilteredSavedVariants, getSavedVariantTableState,
  getSavedVariantVisibleIndices, getSavedVariantTotalPages, getSavedVariantExportConfig,
  getVisibleSortedSavedVariants } from './selectors'

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
    tagOptions: PropTypes.array,
    filters: PropTypes.array,
    discoveryFilters: PropTypes.array,
    loading: PropTypes.bool,
    error: PropTypes.string,
    variantsToDisplay: PropTypes.array,
    totalVariantsCount: PropTypes.number,
    filteredVariantsCount: PropTypes.number,
    variantExportConfig: PropTypes.array,
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
    this.props.history.push(this.props.getUpdateTagUrl(data.value))
  }

  render() {
    const { familyGuid, variantGuid, tag } = this.props.match.params

    const appliedTagCategoryFilter = tag || (variantGuid ? null : (this.props.tableState.categoryFilter || ALL_FILTER))

    let { filters } = this.props
    if (this.props.discoveryFilters) {
      if (appliedTagCategoryFilter === DISCOVERY_CATEGORY_NAME) {
        filters = this.props.discoveryFilters
      }
    }
    if (this.props.totalPages > 1) {
      filters = filters.concat({ ...VARIANT_PAGINATION_FIELD, totalPages: this.props.totalPages })
    }

    const allShown = this.props.variantsToDisplay.length === this.props.totalVariantsCount
    let shownSummary = ''
    if (!allShown) {
      shownSummary = `${this.props.variantsToDisplay.length > 0 ? this.props.firstRecordIndex + 1 : 0}-${this.props.firstRecordIndex + this.props.variantsToDisplay.length} of`
    }

    return (
      <Grid stackable>
        {this.props.tableSummaryComponent && React.createElement(this.props.tableSummaryComponent, {
          familyGuid: variantGuid ? ((this.props.variantsToDisplay[0] || {}).familyGuids || [])[0] : familyGuid,
          ...this.props.tableState,
        })}
        {!this.props.loading &&
          <ControlsRow>
            <Grid.Column width={4}>
              Showing {shownSummary} {this.props.filteredVariantsCount}
              &nbsp;&nbsp;
              <Dropdown
                inline
                options={this.props.tagOptions}
                value={appliedTagCategoryFilter}
                onChange={this.navigateToTag}
              />
              &nbsp;variants {!allShown && `(${this.props.totalVariantsCount} total)`}

            </Grid.Column>
            <Grid.Column width={12} floated="right" textAlign="right">
              {this.props.additionalFilter}
              {!variantGuid &&
                <StateChangeForm
                  updateField={this.props.updateTableField}
                  initialValues={this.props.tableState}
                  fields={filters}
                />
              }
              <HorizontalSpacer width={10} />
              <ExportTableButton downloads={this.props.variantExportConfig} />
            </Grid.Column>
          </ControlsRow>
        }
        <Grid.Row>
          <Grid.Column width={16}>
            <DataLoader
              load={this.props.loadVariants}
              contentId={this.props.match.params}
              reloadOnIdUpdate
              loading={this.props.loading}
              errorMessage={this.props.error && <Message error content={this.props.error} />}
              content={this.props.variantsToDisplay}
            >
              <Variants variants={this.props.variantsToDisplay} />
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
