import React from 'react'
import { Table } from 'semantic-ui-react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { withRouter } from 'react-router'

import { HorizontalSpacer } from 'shared/components/Spacers'
import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import { FamilyLayout } from 'shared/components/panel/family'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { Dropdown } from 'shared/components/form/Inputs'

import { FAMILY_FIELD_RENDER_LOOKUP } from 'shared/utils/constants'

import { getProjectFamilies, getVisibleFamilies, getFamiliesTableState } from '../../../selectors'
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


const TableHeaderRow = ({ headerStatus, showInternalFilters, visibleFamiliesCount, totalFamiliesCount, fields, familiesTableState, updateFamiliesTable: dispatchUpdateFamiliesTable }) => {
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
        <RegularFontHeaderCell>
          Showing &nbsp;
          {
            visibleFamiliesCount !== totalFamiliesCount ?
              <span><b>{visibleFamiliesCount}</b> out of <b>{totalFamiliesCount}</b></span>
              : <span>all <b>{totalFamiliesCount}</b></span>
          }
          &nbsp; families
        </RegularFontHeaderCell>
        <Table.HeaderCell collapsing textAlign="right">
          Search: <FamiliesFilterSearchBox />
        </Table.HeaderCell>
        <Table.HeaderCell collapsing textAlign="right">
          <ReduxFormWrapper
            onSubmit={dispatchUpdateFamiliesTable}
            form="editFamiliesTable"
            initialValues={familiesTableState}
            closeOnSuccess={false}
            submitOnChange
            fields={filterFields}
          />
        </Table.HeaderCell>
        {headerStatus &&
          <Table.HeaderCell collapsing textAlign="right">
            {headerStatus.title}:
            <HorizontalSpacer width={10} />
            <HorizontalStackedBar
              width={100}
              height={14}
              title={headerStatus.title}
              data={headerStatus.data}
            />
          </Table.HeaderCell>
        }
      </Table.Row>
      {fields &&
        <Table.Row>
          <Table.HeaderCell colSpan={5} textAlign="left">
            <FamilyLayout
              compact
              offset
              fields={fields}
              fieldDisplay={field => FAMILY_FIELD_RENDER_LOOKUP[field.id].name}
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
}

const mapStateToProps = (state, ownProps) => ({
  visibleFamiliesCount: getVisibleFamilies(state, ownProps).length,
  totalFamiliesCount: getProjectFamilies(state).length,
  familiesTableState: getFamiliesTableState(state),
})

const mapDispatchToProps = {
  updateFamiliesTable,
}


export { TableHeaderRow as TableHeaderRowComponent }

export default withRouter(connect(mapStateToProps, mapDispatchToProps)(TableHeaderRow))
