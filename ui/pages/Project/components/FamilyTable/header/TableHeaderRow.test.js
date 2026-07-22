import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'
import { FAMILY_FIELD_ID, FAMILY_FIELD_ANALYSIS_STATUS, FAMILY_FIELD_SAVED_VARIANTS } from 'shared/utils/constants'
import { TableHeaderRowComponent } from './TableHeaderRow'
import { CASE_REVIEW_TABLE_NAME } from '../../../constants'

import { STATE_WITH_2_FAMILIES } from '../../../fixtures'

configure({ adapter: new Adapter() })

const noOp = () => {}
const updateFamiliesTableField = () => noOp

const renderHeaderRow = props => mount(
  <Provider store={configureStore()(STATE_WITH_2_FAMILIES)}>
    <table>
      <TableHeaderRowComponent
        familiesTableState={STATE_WITH_2_FAMILIES.familyTableState}
        updateFamiliesTableField={updateFamiliesTableField}
        {...props}
      />
    </table>
  </Provider>,
)

const headerText = wrapper => wrapper.find('th').first().text()
  .replace(/\s+/g, ' ')
  .trim()

test('renders the visible/total family count and search filter', () => {
  const wrapper = renderHeaderRow({ visibleFamiliesCount: 1, totalFamiliesCount: 2 })

  expect(headerText(wrapper)).toEqual('Showing 1 out of 2 families')
  expect(wrapper.find('input[placeholder="Search..."]').exists()).toBe(true)
})

test('renders all families when the visible count matches the total count', () => {
  const wrapper = renderHeaderRow({ visibleFamiliesCount: 2, totalFamiliesCount: 2 })

  expect(headerText(wrapper)).toEqual('Showing all 2 families')
})

test('renders a FamilyLayout row when fields are specified', () => {
  const wrapper = renderHeaderRow({
    visibleFamiliesCount: 2,
    totalFamiliesCount: 2,
    fields: [{ id: FAMILY_FIELD_ID }],
  })

  const familyLayout = wrapper.find({ compact: true, fields: [{ id: FAMILY_FIELD_ID }] })
  expect(familyLayout.exists()).toBe(true)
})

test('renders the case review filter fields when the table is the case review table', () => {
  const wrapper = renderHeaderRow({
    visibleFamiliesCount: 2, totalFamiliesCount: 2, tableName: CASE_REVIEW_TABLE_NAME,
  })

  expect(wrapper.find('input[placeholder="Search..."]').exists()).toBe(true)
})

const ANALYSIS_STATUS_FIELDS = [{ id: FAMILY_FIELD_ANALYSIS_STATUS }]

test('renders a category filter dropdown for a category field with an active filter', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    familyTableFilterState: { R0237_1000_genomes_demo: { analysisStatus: ['ACCEPTED'] } },
  }
  const wrapper = mount(
    <Provider store={configureStore()(state)}>
      <table>
        <TableHeaderRowComponent
          familiesTableState={STATE_WITH_2_FAMILIES.familyTableState}
          updateFamiliesTableField={updateFamiliesTableField}
          visibleFamiliesCount={2}
          totalFamiliesCount={2}
          fields={ANALYSIS_STATUS_FIELDS}
        />
      </table>
    </Provider>,
  )

  const filterIcon = wrapper.find('Icon[name="filter"]')
  expect(filterIcon.exists()).toBe(true)
})

test('renders a saved variants filter dropdown when showVariantDetails is true', () => {
  const wrapper = renderHeaderRow({
    visibleFamiliesCount: 2,
    totalFamiliesCount: 2,
    fields: [{ id: FAMILY_FIELD_ID }],
    showVariantDetails: true,
  })

  const filterDropdown = wrapper.find({ category: FAMILY_FIELD_SAVED_VARIANTS })
  expect(filterDropdown.exists()).toBe(true)
})
