import React from 'react'
import { Table, Popup, Icon } from 'semantic-ui-react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'

import { HorizontalSpacer } from 'shared/components/Spacers'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import { FamilyLayout } from 'shared/components/panel/family'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { Dropdown } from 'shared/components/form/Inputs'

import { FAMILY_FIELD_RENDER_LOOKUP } from 'shared/utils/constants'

import { getProjectFamiliesByGuid, getVisibleFamilies, getFamiliesTableState } from '../../../selectors'
import { updateFamiliesTable } from '../../../reducers'
import { FAMILY_FILTER_OPTIONS, FAMILY_SORT_OPTIONS } from '../../../constants'

import FamiliesFilterSearchBox from './FilterSearchBox'
import SortDirectionToggle from './SortDirectionToggle'

const RegularFontHeaderCell = styled(Table.HeaderCell)`
  font-weight: normal !important;
`

const SpacedDropdown = styled(Dropdown)`
  padding-left: 10px;
  padding-right: 5px;
`


const TableHeaderRow = (
  { headerStatus, showInternalFilters, visibleFamiliesCount, totalFamiliesCount, fields, tableName, familiesTableState,
    updateFamiliesTable: dispatchUpdateFamiliesTable, showVariantTags,
  }) => {
  const filterFields = [
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
    {
      name: 'familiesFilter',
      component: SpacedDropdown,
      inline: true,
      fluid: false,
      selection: true,
      search: true,
      includeCategories: true,
      label: 'Filter:',
      options: FAMILY_FILTER_OPTIONS.filter((f) => { return showInternalFilters ? !f.internalOmit : !f.internalOnly }),
    },
  ]

  return (
    <Table.Header fullWidth>
      <Table.Row>
        <RegularFontHeaderCell width={2}>
          Showing &nbsp;
          {
            visibleFamiliesCount !== totalFamiliesCount ?
              <span><b>{visibleFamiliesCount}</b> out of <b>{totalFamiliesCount}</b></span>
              : <span>all <b>{totalFamiliesCount}</b></span>
          }
          &nbsp; families
        </RegularFontHeaderCell>
        <Table.HeaderCell width={14} textAlign="right">
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
            fields={filterFields}
          />
          <HorizontalSpacer width={20} />
          {headerStatus.title}:
          <HorizontalSpacer width={10} />
          <HorizontalStackedBar
            width={100}
            height={14}
            title={headerStatus.title}
            data={headerStatus.data}
          />
        </Table.HeaderCell>
      </Table.Row>
      {fields &&
        <Table.Row>
          <Table.HeaderCell colSpan={2} textAlign="left">
            <FamilyLayout
              compact
              offset
              fields={fields}
              fieldDisplay={field => FAMILY_FIELD_RENDER_LOOKUP[field.id].name}
              rightContent={showVariantTags ? 'Saved Variants' : null}
            />
          </Table.HeaderCell>
        </Table.Row>
      }
    </Table.Header>
  )
}

TableHeaderRow.propTypes = {
  headerStatus: PropTypes.object,
  showInternalFilters: PropTypes.bool,
  visibleFamiliesCount: PropTypes.number,
  totalFamiliesCount: PropTypes.number,
  familiesTableState: PropTypes.object,
  updateFamiliesTable: PropTypes.func,
  fields: PropTypes.array,
  tableName: PropTypes.string,
  showVariantTags: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  visibleFamiliesCount: getVisibleFamilies(state, ownProps).length,
  totalFamiliesCount: Object.keys(getProjectFamiliesByGuid(state)).length,
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
