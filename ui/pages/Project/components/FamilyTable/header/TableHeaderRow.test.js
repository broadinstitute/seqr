import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { FAMILY_FIELD_ID, FAMILY_FIELD_ANALYSIS_STATUS, FAMILY_FIELD_SAVED_VARIANTS } from 'shared/utils/constants'
import TableHeaderRow from './TableHeaderRow'
import { CASE_REVIEW_TABLE_NAME } from '../../../constants'

import { STATE_WITH_2_FAMILIES } from '../../../fixtures'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

const renderHeaderRow = (props, state = STATE_WITH_2_FAMILIES) => mount(
  <Provider store={configureStore(state)}>
    <table>
      <TableHeaderRow {...props} />
    </table>
  </Provider>,
)

const headerText = wrapper => wrapper.find('th').first().text()
  .replace(/\s+/g, ' ')
  .trim()

test('renders the visible/total family count and search filter', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    familyTableState: { ...STATE_WITH_2_FAMILIES.familyTableState, familiesSearch: '1' },
  }
  const wrapper = renderHeaderRow({}, state)

  expect(headerText(wrapper)).toEqual('Showing 1 out of 2 families')
  expect(wrapper.find('input[placeholder="Search..."]').exists()).toBe(true)
})

test('renders all families when the visible count matches the total count', () => {
  const wrapper = renderHeaderRow({})

  expect(headerText(wrapper)).toEqual('Showing all 2 families')
})

test('renders a FamilyLayout row when fields are specified', () => {
  const wrapper = renderHeaderRow({ fields: [{ id: FAMILY_FIELD_ID }] })

  const familyLayout = wrapper.find({ compact: true, fields: [{ id: FAMILY_FIELD_ID }] })
  expect(familyLayout.exists()).toBe(true)
})

test('renders the case review filter fields when the table is the case review table', () => {
  const wrapper = renderHeaderRow({ tableName: CASE_REVIEW_TABLE_NAME })

  expect(wrapper.find('input[placeholder="Search..."]').exists()).toBe(true)
})

const ANALYSIS_STATUS_FIELDS = [{ id: FAMILY_FIELD_ANALYSIS_STATUS }]

test('renders a category filter dropdown for a category field with an active filter', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    familyTableFilterState: { R0237_1000_genomes_demo: { analysisStatus: ['ACCEPTED'] } },
  }
  const wrapper = renderHeaderRow({ fields: ANALYSIS_STATUS_FIELDS }, state)

  const filterIcon = wrapper.find('Icon[name="filter"]')
  expect(filterIcon.exists()).toBe(true)
})

test('renders a saved variants filter dropdown when showVariantDetails is true', () => {
  const wrapper = renderHeaderRow({
    fields: [{ id: FAMILY_FIELD_ID }],
    showVariantDetails: true,
  })

  const filterDropdown = wrapper.find({ category: FAMILY_FIELD_SAVED_VARIANTS })
  expect(filterDropdown.exists()).toBe(true)
})

test('dispatches an update to the families table state when the search filter changes', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <table>
        <TableHeaderRow
          familiesTableState={STATE_WITH_2_FAMILIES.familyTableState}
          visibleFamiliesCount={1}
          totalFamiliesCount={2}
        />
      </table>
    </Provider>,
  )

  wrapper.find('input[placeholder="Search..."]').simulate('change', { target: { value: 'foo' } })

  expect(store.getActions()).toContainEqual({
    type: 'UPDATE_FAMILY_TABLE_STATE',
    updates: { familiesSearch: 'foo' },
  })
})

test('dispatches a case review table state update when the table is the case review table', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <table>
        <TableHeaderRow
          tableName={CASE_REVIEW_TABLE_NAME}
          familiesTableState={STATE_WITH_2_FAMILIES.caseReviewTableState}
          visibleFamiliesCount={1}
          totalFamiliesCount={2}
        />
      </table>
    </Provider>,
  )

  wrapper.find('input[placeholder="Search..."]').simulate('change', { target: { value: 'foo' } })

  expect(store.getActions()).toContainEqual({
    type: 'UPDATE_CASE_REVIEW_TABLE_STATE',
    updates: { familiesSearch: 'foo' },
  })
})

test('dispatches an update to the families table filter state when a category filter changes', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <table>
        <TableHeaderRow
          familiesTableState={STATE_WITH_2_FAMILIES.familyTableState}
          visibleFamiliesCount={2}
          totalFamiliesCount={2}
          fields={ANALYSIS_STATUS_FIELDS}
        />
      </table>
    </Provider>,
  )

  wrapper.find('BaseFamilyTableFilter').first().props().updateNestedFilter(FAMILY_FIELD_ANALYSIS_STATUS)(['ACCEPTED'])

  expect(store.getActions()).toContainEqual({
    type: 'UPDATE_FAMILY_TABLE_FILTER_STATE',
    updatesById: { R0237_1000_genomes_demo: { analysisStatus: ['ACCEPTED'] } },
  })
})
