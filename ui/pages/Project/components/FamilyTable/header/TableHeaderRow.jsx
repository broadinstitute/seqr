import React from 'react'
import { Table, Icon } from 'semantic-ui-react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'

import FamilyLayout from 'shared/components/panel/family/FamilyLayout'
import StateChangeForm from 'shared/components/form/StateChangeForm'
import { Dropdown, BaseSemanticInput } from 'shared/components/form/Inputs'

import { FAMILY_FIELD_NAME_LOOKUP, FAMILY_FIELD_SAVED_VARIANTS } from 'shared/utils/constants'

import {
  getProjectAnalysisGroupFamiliesByGuid, getVisibleFamilies, getFamiliesTableState, getFamiliesTableFilters,
  getFamiliesFilterOptionsByCategory,
} from '../../../selectors'
import { updateFamiliesTable, updateFamiliesTableFilters } from '../../../reducers'
import {
  CATEGORY_FAMILY_FILTERS,
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
  
  td {
     overflow: visible !important;
  }
`

const SpacedDropdown = styled(Dropdown)`
  padding-left: 10px;
  padding-right: 5px;
`

const FilterMultiDropdown = styled(Dropdown).attrs({ inline: true, multiple: true, search: true, icon: null })`
  .ui.multiple.dropdown {
    width: 100%;
  
    .label, .search, .sizer {
      display: none;
      white-space: nowrap;
    }
    
    &.active.visible {
      border: 1px solid rgba(34,36,38,.15);
      border-radius: 0.28571429rem;
      background-color: white;
      z-index: 10;
    
      .trigger {
        display: none;
      }
      .label, .search {
        display: inline-block;
      }
    }
  }
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
const FILTER_FIELDS = [FAMILY_SEARCH, ...SORT_FILTER_FIELDS]
const CASE_REVEIW_FILTER_FIELDS = [
  FAMILY_SEARCH, { ...FAMILY_FILTER, options: CASE_REVIEW_FAMILY_FILTER_OPTIONS }, ...SORT_FILTER_FIELDS,
]

const renderLabel = label => ({ color: 'blue', content: label.text })

const BaseFamilyTableFilter = ({ nestedFilterState, updateNestedFilter, options, category }) => {
  const value = (nestedFilterState || {})[category] || []
  return (
    <FilterMultiDropdown
      name={category}
      value={value}
      onChange={updateNestedFilter(category)}
      options={options}
      trigger={
        <span className="trigger">
          <Icon name={value.length ? 'filter' : 'caret down'} size="small" />
          {FAMILY_FIELD_NAME_LOOKUP[category]}
        </span>
      }
      renderLabel={renderLabel}
      includeCategories
    />
  )
}

BaseFamilyTableFilter.propTypes = {
  nestedFilterState: PropTypes.object,
  updateNestedFilter: PropTypes.func.isRequired,
  category: PropTypes.string.isRequired,
  options: PropTypes.arrayOf(PropTypes.object),
}

const mapFilterStateToProps = (state, ownProps) => ({
  nestedFilterState: getFamiliesTableFilters(state),
  options: getFamiliesFilterOptionsByCategory(state)[ownProps.category],
})

const mapFilterDispatchToProps = dispatch => ({
  updateNestedFilter: category => (value) => {
    dispatch(updateFamiliesTableFilters({ [category]: value }))
  },
})

const FamilyTableFilter = connect(mapFilterStateToProps, mapFilterDispatchToProps)(BaseFamilyTableFilter)

const familyFieldDisplay = (field) => {
  const { id } = field
  return CATEGORY_FAMILY_FILTERS[id] ? <FamilyTableFilter category={id} /> : FAMILY_FIELD_NAME_LOOKUP[id]
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
              &nbsp; out of &nbsp;
              <b>{totalFamiliesCount}</b>
            </span>
          ) : (
            <span>
              all &nbsp;
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
        <OverflowHeaderCell colSpan={2} textAlign="left">
          <FamilyLayout
            compact
            fields={fields}
            fieldDisplay={familyFieldDisplay}
            rightContent={showVariantDetails ? <FamilyTableFilter category={FAMILY_FIELD_SAVED_VARIANTS} /> : null}
          />
        </OverflowHeaderCell>
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
