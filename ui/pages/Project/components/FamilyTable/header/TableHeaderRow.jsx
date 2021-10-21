import React from 'react'
import { Table } from 'semantic-ui-react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'

import FamilyLayout from 'shared/components/panel/family/FamilyLayout'
import StateChangeForm from 'shared/components/form/StateChangeForm'
import { Dropdown, BaseSemanticInput } from 'shared/components/form/Inputs'

import { FAMILY_FIELD_NAME_LOOKUP } from 'shared/utils/constants'

import { getProjectAnalysisGroupFamiliesByGuid, getVisibleFamilies, getFamiliesTableState } from '../../../selectors'
import { updateFamiliesTable } from '../../../reducers'
import {
  FAMILY_FILTER_OPTIONS,
  CASE_REVIEW_FAMILY_FILTER_OPTIONS,
  FAMILY_SORT_OPTIONS,
  CASE_REVIEW_TABLE_NAME,
} from '../../../constants'

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

const FAMILY_SEARCH = {
  name: 'familiesSearch',
  component: BaseSemanticInput,
  inputType: 'Input',
  placeholder: 'Search...',
  inline: true,
  label: 'Search',
  labelHelp: 'Filter families by searching on family name or individual phenotypes',
}

const FAMILY_FILTER = {
  name: 'familiesFilter',
  component: SpacedDropdown,
  inline: true,
  fluid: false,
  selection: true,
  search: true,
  includeCategories: true,
  label: 'Filter',
}
const SORT_FILTER_FIELDS = [
  {
    name: 'familiesSortOrder',
    component: SpacedDropdown,
    inline: true,
    fluid: false,
    selection: true,
    label: 'Sort By',
    options: FAMILY_SORT_OPTIONS,
  },
  {
    name: 'familiesSortDirection',
    component: SortDirectionToggle,
  },
]
const FILTER_FIELDS = [FAMILY_SEARCH, { ...FAMILY_FILTER, options: FAMILY_FILTER_OPTIONS }, ...SORT_FILTER_FIELDS]
const CASE_REVEIW_FILTER_FIELDS = [
  FAMILY_SEARCH, { ...FAMILY_FILTER, options: CASE_REVIEW_FAMILY_FILTER_OPTIONS }, ...SORT_FILTER_FIELDS,
]

const familyFieldDisplay = field => FAMILY_FIELD_NAME_LOOKUP[field.id]

export const TableHeaderDetail = React.memo(({ fields, offset, showVariantDetails }) => (
  <FamilyLayout
    compact
    offset={offset}
    fields={fields}
    fieldDisplay={familyFieldDisplay}
    rightContent={showVariantDetails ? 'Saved Variants' : null}
  />
))

TableHeaderDetail.propTypes = {
  offset: PropTypes.bool,
  fields: PropTypes.arrayOf(PropTypes.object),
  showVariantDetails: PropTypes.bool,
}

const TableHeaderRow = React.memo(({
  visibleFamiliesCount, totalFamiliesCount, fields, tableName, familiesTableState, updateFamiliesTableField,
  showVariantDetails,
}) => (
  <Table.Header fullWidth>
    <Table.Row>
      <RegularFontHeaderCell width={5}>
        Showing &nbsp;
        {
          visibleFamiliesCount !== totalFamiliesCount ? (
            <span>
              <b>{visibleFamiliesCount}</b>
              out of
              <b>{totalFamiliesCount}</b>
            </span>
          ) : (
            <span>
              all
              <b>{totalFamiliesCount}</b>
            </span>
          )
        }
        &nbsp; families
      </RegularFontHeaderCell>
      <OverflowHeaderCell width={16} textAlign="right">
        <StateChangeForm
          initialValues={familiesTableState}
          updateField={updateFamiliesTableField}
          fields={(tableName === CASE_REVIEW_TABLE_NAME ? CASE_REVEIW_FILTER_FIELDS : FILTER_FIELDS)}
        />
      </OverflowHeaderCell>
    </Table.Row>
    {fields && (
      <Table.Row>
        <Table.HeaderCell colSpan={2} textAlign="left">
          <TableHeaderDetail fields={fields} showVariantDetails={showVariantDetails} offset />
        </Table.HeaderCell>
      </Table.Row>
    )}
  </Table.Header>
))

TableHeaderRow.propTypes = {
  visibleFamiliesCount: PropTypes.number.isRequired,
  totalFamiliesCount: PropTypes.number.isRequired,
  familiesTableState: PropTypes.object.isRequired,
  updateFamiliesTableField: PropTypes.func.isRequired,
  fields: PropTypes.arrayOf(PropTypes.object),
  tableName: PropTypes.string,
  showVariantDetails: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  visibleFamiliesCount: getVisibleFamilies(state, ownProps).length,
  totalFamiliesCount: Object.keys(getProjectAnalysisGroupFamiliesByGuid(state, ownProps)).length,
  familiesTableState: getFamiliesTableState(state, ownProps),
})

const mapDispatchToProps = (dispatch, ownProps) => ({
  updateFamiliesTableField: field => (value) => {
    dispatch(updateFamiliesTable({ [field]: value }, ownProps.tableName))
  },
})

export { TableHeaderRow as TableHeaderRowComponent }

export default connect(mapStateToProps, mapDispatchToProps)(TableHeaderRow)
