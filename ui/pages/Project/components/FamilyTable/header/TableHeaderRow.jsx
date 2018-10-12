import React from 'react'
import { Table, Popup, Icon } from 'semantic-ui-react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'

import { HorizontalSpacer } from 'shared/components/Spacers'
import { FamilyLayout } from 'shared/components/panel/family'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { Dropdown } from 'shared/components/form/Inputs'

import { FAMILY_FIELD_RENDER_LOOKUP } from 'shared/utils/constants'

import { getProjectAnalysisGroupFamiliesByGuid, getVisibleFamilies, getFamiliesTableState } from '../../../selectors'
import { updateFamiliesTable } from '../../../reducers'
import { FAMILY_FILTER_OPTIONS, FAMILY_SORT_OPTIONS } from '../../../constants'

import FamiliesFilterSearchBox from './FilterSearchBox'
import SortDirectionToggle from './SortDirectionToggle'

const RegularFontHeaderCell = styled(Table.HeaderCell)`
  font-weight: normal !important;
`


// Allows dropdowns to be visible inside table cell
const OverflowHeaderCell = styled(Table.HeaderCell)`
  overflow: visible !important;
`

const SpacedDropdown = styled(Dropdown)`
  padding-left: 10px;
  padding-right: 5px;
`

const FAMILY_FILTER = {
  name: 'familiesFilter',
  component: SpacedDropdown,
  inline: true,
  fluid: false,
  selection: true,
  search: true,
  includeCategories: true,
  label: 'Filter:',
}
const SORT_FILTER_FIELDS = [
  {
    name: 'familiesSortOrder',
    component: SpacedDropdown,
    inline: true,
    fluid: false,
    selection: true,
    label: 'Sort By:',
    options: FAMILY_SORT_OPTIONS,
  },
  {
    name: 'familiesSortDirection',
    component: SortDirectionToggle,
  },
]
const FILTER_FIELDS = [{ ...FAMILY_FILTER, options: FAMILY_FILTER_OPTIONS.filter(f => !f.internalOnly) }, ...SORT_FILTER_FIELDS]
const INTERNAL_FILTER_FIELDS = [{ ...FAMILY_FILTER, options: FAMILY_FILTER_OPTIONS.filter(f => !f.internalOmit) }, ...SORT_FILTER_FIELDS]

export const TableHeaderDetail = ({ fields, offset, showVariantDetails }) =>
  <FamilyLayout
    compact
    offset={offset}
    fields={fields}
    fieldDisplay={field => FAMILY_FIELD_RENDER_LOOKUP[field.id].name}
    rightContent={showVariantDetails ? 'Saved Variants' : null}
  />


TableHeaderDetail.propTypes = {
  offset: PropTypes.bool,
  fields: PropTypes.array,
  showVariantDetails: PropTypes.bool,
}

const TableHeaderRow = (
  { showInternalFilters, visibleFamiliesCount, totalFamiliesCount, fields, tableName, familiesTableState,
    updateFamiliesTable: dispatchUpdateFamiliesTable, showVariantDetails,
  }) =>
    <Table.Header fullWidth>
      <Table.Row>
        <RegularFontHeaderCell width={5}>
          Showing &nbsp;
          {
            visibleFamiliesCount !== totalFamiliesCount ?
              <span><b>{visibleFamiliesCount}</b> out of <b>{totalFamiliesCount}</b></span>
              : <span>all <b>{totalFamiliesCount}</b></span>
          }
          &nbsp; families
        </RegularFontHeaderCell>
        <OverflowHeaderCell width={16} textAlign="right">
          <Popup
            content="Filter families by searching on family name or individual phenotypes"
            position="top center"
            trigger={<a><Icon name="info circle" link /></a>}
          />
          Search:
          <HorizontalSpacer width={10} />
          <FamiliesFilterSearchBox />
          <HorizontalSpacer width={20} />
          <ReduxFormWrapper
            onSubmit={dispatchUpdateFamiliesTable}
            form={`edit${tableName}FamiliesTable`}
            initialValues={familiesTableState}
            closeOnSuccess={false}
            submitOnChange
            inline
            fields={showInternalFilters ? INTERNAL_FILTER_FIELDS : FILTER_FIELDS}
          />
        </OverflowHeaderCell>
      </Table.Row>
      {fields &&
        <Table.Row>
          <Table.HeaderCell colSpan={2} textAlign="left">
            <TableHeaderDetail fields={fields} showVariantDetails={showVariantDetails} offset />
          </Table.HeaderCell>
        </Table.Row>
      }
    </Table.Header>

TableHeaderRow.propTypes = {
  showInternalFilters: PropTypes.bool,
  visibleFamiliesCount: PropTypes.number.isRequired,
  totalFamiliesCount: PropTypes.number.isRequired,
  familiesTableState: PropTypes.object.isRequired,
  updateFamiliesTable: PropTypes.func.isRequired,
  fields: PropTypes.array,
  tableName: PropTypes.string,
  showVariantDetails: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  visibleFamiliesCount: getVisibleFamilies(state, ownProps).length,
  totalFamiliesCount: Object.keys(getProjectAnalysisGroupFamiliesByGuid(state, ownProps)).length,
  familiesTableState: getFamiliesTableState(state, ownProps),
})

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    updateFamiliesTable: (updates) => {
      dispatch(updateFamiliesTable(updates, ownProps.tableName))
    },
  }
}

export { TableHeaderRow as TableHeaderRowComponent }

export default connect(mapStateToProps, mapDispatchToProps)(TableHeaderRow)
