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
    familyTableFiltersByProject: null,
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

test('renders correctly when a family has no analysedBy list', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    familiesByGuid: {
      ...STATE_WITH_2_FAMILIES.familiesByGuid,
      F011652_1: {
        ...STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1,
        analysedBy: undefined,
      },
    },
  }
  const wrapper = renderHeaderRow({ fields: [{ id: FAMILY_FIELD_ANALYSIS_STATUS }] }, state)

  expect(wrapper.find('BaseFamilyTableFilter').exists()).toBe(true)
})

test('renders correctly when there is no families table filter state for the current project', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    familyTableFilterState: {},
  }
  const wrapper = renderHeaderRow({ fields: [{ id: FAMILY_FIELD_ANALYSIS_STATUS }] }, state)

  expect(headerText(wrapper)).toEqual('Showing all 2 families')
})

test('filters visible families by matching saved variant tag types and excludes non-matching families', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    familyTableFilterState: { R0237_1000_genomes_demo: { savedVariants: ['Review'] } },
  }
  const wrapper = renderHeaderRow({}, state)

  expect(headerText(wrapper)).toEqual('Showing 1 out of 2 families')
})

test('filters visible families by case review status, falling back to family.caseReviewStatuses when an individual is missing', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    familiesByGuid: {
      ...STATE_WITH_2_FAMILIES.familiesByGuid,
      F011652_1: {
        ...STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1,
        individualGuids: ['MISSING_INDIVIDUAL_GUID'],
        caseReviewStatuses: ['I', 'I', 'I'],
      },
    },
    familyTableFilterState: { R0237_1000_genomes_demo: { analysisStatus: ['IN_REVIEW'] } },
  }
  const wrapper = renderHeaderRow({}, state)

  // F011652_1 falls back to family.caseReviewStatuses (all in review), F011652_2's individuals'
  // statuses are a mix of in-review/accepted so it does not pass the every()-based in-review filter
  expect(headerText(wrapper)).toEqual('Showing 1 out of 2 families')
})

test('filters visible families using the case review "assigned to me - in review" filter', () => {
  const inReviewState = {
    ...STATE_WITH_2_FAMILIES,
    familiesByGuid: {
      ...STATE_WITH_2_FAMILIES.familiesByGuid,
      F011652_1: {
        ...STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1,
        assignedAnalyst: { email: STATE_WITH_2_FAMILIES.user.email },
        individualGuids: ['I021476_na19678_1', 'I021474_na19679_1', 'I021475_na19675_1'],
      },
      F011652_2: {
        ...STATE_WITH_2_FAMILIES.familiesByGuid.F011652_2,
        assignedAnalyst: { email: STATE_WITH_2_FAMILIES.user.email },
      },
    },
    individualsByGuid: {
      ...STATE_WITH_2_FAMILIES.individualsByGuid,
      I021476_na19678_1: { ...STATE_WITH_2_FAMILIES.individualsByGuid.I021476_na19678_1, caseReviewStatus: 'I' },
      I021474_na19679_1: { ...STATE_WITH_2_FAMILIES.individualsByGuid.I021474_na19679_1, caseReviewStatus: 'I' },
      I021475_na19675_1: { ...STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1, caseReviewStatus: 'I' },
    },
    caseReviewTableState: { familiesFilter: 'SHOW_ASSIGNED_TO_ME_IN_REVIEW' },
  }
  const wrapper = renderHeaderRow({ tableName: CASE_REVIEW_TABLE_NAME }, inReviewState)

  // F011652_1 is assigned to the current user and fully in review, F011652_2 is assigned but not in review
  expect(headerText(wrapper)).toEqual('Showing 1 out of 2 families')
})

test('filters visible families by required metadata presence/absence', () => {
  const noIndividualsState = {
    ...STATE_WITH_2_FAMILIES,
    familiesByGuid: {
      ...STATE_WITH_2_FAMILIES.familiesByGuid,
      F011652_1: {
        ...STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1,
        individualGuids: [],
        hasRequiredMetadata: true,
      },
    },
    familyTableFilterState: { R0237_1000_genomes_demo: { firstSample: ['SHOW_PHENOTYPES_ENTERED'] } },
  }
  const wrapperNoIndividuals = renderHeaderRow({}, noIndividualsState)
  expect(headerText(wrapperNoIndividuals)).toEqual('Showing 1 out of 2 families')

  const requiredFieldsState = {
    ...STATE_WITH_2_FAMILIES,
    individualsByGuid: {
      ...STATE_WITH_2_FAMILIES.individualsByGuid,
      I021476_na19678_1: {
        ...STATE_WITH_2_FAMILIES.individualsByGuid.I021476_na19678_1,
        probandRelationship: false,
        population: 'AFR',
        features: [{ id: 'HP:0001631' }],
      },
      I021474_na19679_1: {
        ...STATE_WITH_2_FAMILIES.individualsByGuid.I021474_na19679_1,
        probandRelationship: undefined,
        population: undefined,
        features: [],
      },
    },
    familyTableFilterState: { R0237_1000_genomes_demo: { firstSample: ['SHOW_NO_PHENOTYPES_ENTERED'] } },
  }
  const wrapperRequiredFields = renderHeaderRow({}, requiredFieldsState)
  expect(headerText(wrapperRequiredFields)).toEqual('Showing 1 out of 2 families')
})
