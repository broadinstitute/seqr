import React from 'react'
import { shallow, mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import { FAMILY_MAIN_FIELDS, FAMILY_DETAIL_FIELDS } from 'shared/utils/constants'

import cloneDeep from 'lodash/cloneDeep'
import { flushAll } from 'shared/utils/testHelpers'
import FamilyTable from './FamilyTable'
import { STATE_WITH_2_FAMILIES } from '../../fixtures'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

const renderTable = state => mount(
  <Provider store={configureStore(state)}>
    <MemoryRouter>
      <FamilyTable
        detailFields={FAMILY_DETAIL_FIELDS}
        noDetailFields={FAMILY_MAIN_FIELDS}
      />
    </MemoryRouter>
  </Provider>,
)

test('toggles compact/full family details', () => {
  const wrapper = renderTable(STATE_WITH_2_FAMILIES)

  // the family name field is always rendered in addition to the toggled field set
  const NAME_FIELD_COUNT = 1
  const CORE_FIELD_COUNT = FAMILY_MAIN_FIELDS.length + NAME_FIELD_COUNT
  const DETAIL_FIELD_COUNT = FAMILY_DETAIL_FIELDS.length + NAME_FIELD_COUNT

  // starts collapsed - only the compact noDetailFields are rendered
  const rows = wrapper.find('FamilyTableRow')
  expect(rows.length).toEqual(2)
  expect(rows.find({ familyGuid: 'F011652_1' }).exists()).toBe(true)
  expect(rows.find({ familyGuid: 'F011652_1' }).find('BaseFieldView').length).toEqual(CORE_FIELD_COUNT)
  expect(rows.find({ familyGuid: 'F011652_2' }).find('BaseFieldView').length).toEqual(CORE_FIELD_COUNT)

  const toggle = rows.find({ familyGuid: 'F011652_1' }).find('CollapsableLayout').find('Icon[name="dropdown"]')
  expect(toggle.exists()).toBe(true)

  toggle.first().simulate('click')
  wrapper.update()

  // after toggling, the full detailFields are rendered instead for the toggled row
  expect(wrapper.find('FamilyTableRow').find({ familyGuid: 'F011652_2' }).find('BaseFieldView').length).toEqual(CORE_FIELD_COUNT)
  const toggledRow = wrapper.find('FamilyTableRow').find({ familyGuid: 'F011652_1' }).first()
  expect(toggledRow.find('Family').find('BaseFieldView').length).toEqual(DETAIL_FIELD_COUNT)
  expect(toggledRow.find('IndividualRow').length).toEqual(3)
})

test('renders a loading indicator while families are loading', () => {
  const loadingState = {
    ...STATE_WITH_2_FAMILIES,
    familiesLoading: { isLoading: true },
  }
  const wrapper = renderTable(loadingState)

  expect(wrapper.find('Loader').exists()).toBe(true)
  expect(wrapper.find('FamilyTableRow').length).toEqual(0)
})

test('renders an empty message when there are no visible families', () => {
  const emptyState = {
    ...STATE_WITH_2_FAMILIES,
    familiesByGuid: {},
  }
  const wrapper = renderTable(emptyState)

  expect(wrapper.find('FamilyTableRow').length).toEqual(0)
  expect(wrapper.text()).toContain('0 families found')

  // Popup content is a portal only rendered on hover/click, so render its `content` prop directly
  const popupContent = wrapper.find('Popup[on="click"]').prop('content')
  const popupWrapper = shallow(popupContent)
  const exportUrls = popupWrapper.root().prop('downloads')
  const familiesData = exportUrls.find(({ name }) => name === 'Families').getRawData(emptyState)
  expect(familiesData).toEqual([])
  const individualsData = exportUrls.find(({ name }) => name === 'Individuals').getRawData(emptyState)
  expect(individualsData).toEqual([])
  const samplesData = exportUrls.find(({ name }) => name === 'Samples').getRawData(emptyState)
  expect(samplesData).toEqual([])
})

test('loads export data when the export popup content is rendered', async () => {
  const wrapper = renderTable(STATE_WITH_2_FAMILIES)

  fetch.mockClear()

  // Popup content is a portal only rendered on hover/click, so render its `content` prop directly
  const popupContent = wrapper.find('Popup[on="click"]').prop('content')
  const popupWrapper = shallow(popupContent)
  await flushAll()

  const requestedUrls = fetch.mock.calls.map(([url]) => url)
  expect(requestedUrls.some(
    url => url.includes(`/api/project/${STATE_WITH_2_FAMILIES.currentProjectGuid}/get_individuals`),
  )).toBe(true)
  expect(requestedUrls.some(
    url => url.includes(`/api/project/${STATE_WITH_2_FAMILIES.currentProjectGuid}/get_family_notes`),
  )).toBe(true)

  const exportUrls = popupWrapper.root().prop('downloads')
  expect(exportUrls.find(({ name }) => name === 'Families').filename).not.toContain('case_review')
  const familiesData = exportUrls.find(({ name }) => name === 'Families').getRawData(STATE_WITH_2_FAMILIES)
  expect(familiesData.find(f => f.familyGuid === 'F011652_2').analysisNotes).toBeDefined()
  expect(familiesData.find(f => f.familyGuid === 'F011652_1').analysisNotes).toBeUndefined()

  const missingIndividualsState = cloneDeep(STATE_WITH_2_FAMILIES)
  missingIndividualsState.familiesByGuid.F_NO_INDIVIDUALS = {
    ...missingIndividualsState.familiesByGuid.F011652_1,
    familyGuid: 'F_NO_INDIVIDUALS',
    familyId: 'F_NO_INDIVIDUALS',
    individualGuids: [],
  }
  const individualsData = exportUrls.find(({ name }) => name === 'Individuals').getRawData(missingIndividualsState)
  // the family with no individuals contributes no rows, so the
  // total row count is unchanged from the original 2-family state
  expect(individualsData.length).toEqual(6)

  const samplesData = exportUrls.find(({ name }) => name === 'Samples').getRawData(STATE_WITH_2_FAMILIES)
  expect(samplesData.length).toBeGreaterThan(0)
})

test('falls back to unsorted families when sort order is invalid or a family is missing a familyId', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    familyTableState: { ...STATE_WITH_2_FAMILIES.familyTableState, familiesSortOrder: '' },
  }
  const wrapper = renderTable(state)
  expect(wrapper.find('FamilyTableRow').length).toEqual(2)

  const invalidSortState = {
    ...STATE_WITH_2_FAMILIES,
    familyTableState: { ...STATE_WITH_2_FAMILIES.familyTableState, familiesSortOrder: 'NOT_A_REAL_SORT_ORDER' },
  }
  const invalidWrapper = renderTable(invalidSortState)
  expect(invalidWrapper.find('FamilyTableRow').map(content => content.prop('familyGuid'))).toEqual(['F011652_1', 'F011652_2'])

  const missingFamilyIdState = cloneDeep(STATE_WITH_2_FAMILIES)
  delete missingFamilyIdState.familiesByGuid.F011652_1.familyId
  const missingIdWrapper = renderTable(missingFamilyIdState)
  expect(missingIdWrapper.find('FamilyTableRow').map(content => content.prop('familyGuid'))).toEqual(['F011652_1', 'F011652_2'])
})


test('sorts visible families by date loaded, falling back when a family has no loaded dataset', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    familyTableState: { ...STATE_WITH_2_FAMILIES.familyTableState, familiesSortOrder: 'DATA_LOADED_DATE' },
  }
  const wrapper = renderTable(state)
  expect(wrapper.find('FamilyTableRow').map(content => content.prop('familyGuid'))).toEqual(['F011652_2', 'F011652_1'])


  const firstLoadedState = {
    ...STATE_WITH_2_FAMILIES,
    familyTableState: { ...STATE_WITH_2_FAMILIES.familyTableState, familiesSortOrder: 'DATA_FIRST_LOADED_DATE' },
  }
  const firstLoadedWrapper = renderTable(firstLoadedState)
  expect(firstLoadedWrapper.find('FamilyTableRow').map(content => content.prop('familyGuid'))).toEqual(['F011652_2', 'F011652_1'])

  const addedDateSortState = {
    ...STATE_WITH_2_FAMILIES,
    familyTableState: { ...STATE_WITH_2_FAMILIES.familyTableState, familiesSortOrder: 'FAMILY_ADDED_DATE' },
  }
  const addedDateSortWrapper = renderTable(addedDateSortState)
  expect(addedDateSortWrapper.find('FamilyTableRow').map(content => content.prop('familyGuid'))).toEqual(['F011652_2', 'F011652_1'])
})

test('sorts visible families by analysis status, falling back when the status is not in the lookup', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    familiesByGuid: {
      ...STATE_WITH_2_FAMILIES.familiesByGuid,
      F011652_1: { ...STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1, analysisStatus: 'NOT_A_REAL_STATUS' },
    },
    familyTableState: { ...STATE_WITH_2_FAMILIES.familyTableState, familiesSortOrder: 'SORT_BY_ANALYSIS_STATUS' },
  }
  const wrapper = renderTable(state)
  expect(wrapper.find('FamilyTableRow').map(content => content.prop('familyGuid'))).toEqual(['F011652_1', 'F011652_2'])
})

test('sorts visible families by analysed date, only counting SNP analysedBy entries and falling back when there are none', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    familiesByGuid: {
      ...STATE_WITH_2_FAMILIES.familiesByGuid,
      F011652_1: {
        ...STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1,
        analysedBy: [
          { dataType: 'SNP', lastModifiedDate: '2020-01-01T01:00:00.000Z', createdBy: 'user1' },
          { dataType: 'SV', lastModifiedDate: '2022-01-01T01:00:00.000Z', createdBy: 'user2' },
        ],
      },
      F011652_2: { ...STATE_WITH_2_FAMILIES.familiesByGuid.F011652_2, analysedBy: [] },
    },
    familyTableState: { ...STATE_WITH_2_FAMILIES.familyTableState, familiesSortOrder: 'SORT_BY_ANALYSED_DATE' },
  }
  const wrapper = renderTable(state)
  expect(wrapper.find('FamilyTableRow').map(content => content.prop('familyGuid'))).toEqual(['F011652_1', 'F011652_2'])

  const filteredState = {
    ...state,
    familyTableState: { ...state.familyTableState, familiesSearch: 'user2' },
  }
  const filteredWrapper = renderTable(filteredState)
  expect(filteredWrapper.find('FamilyTableRow').map(content => content.prop('familyGuid'))).toEqual(['F011652_1'])
})

test('sorts visible families by review status changed date, handling missing individuals and comparing multiple modified dates', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    familiesByGuid: {
      ...STATE_WITH_2_FAMILIES.familiesByGuid,
      F011652_1: {
        ...STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1,
        individualGuids: ['MISSING_INDIVIDUAL_GUID', 'I021476_na19678_1', 'I021474_na19679_1'],
        caseReviewStatusLastModified: '2010-01-01T01:00:00.000Z',
      },
      F011652_2: {
        ...STATE_WITH_2_FAMILIES.familiesByGuid.F011652_2,
        individualGuids: [],
        caseReviewStatusLastModified: undefined,
      },
    },
    individualsByGuid: {
      ...STATE_WITH_2_FAMILIES.individualsByGuid,
      I021476_na19678_1: {
        ...STATE_WITH_2_FAMILIES.individualsByGuid.I021476_na19678_1,
        caseReviewStatusLastModifiedDate: '2018-01-01T01:00:00.000Z',
      },
      I021474_na19679_1: {
        ...STATE_WITH_2_FAMILIES.individualsByGuid.I021474_na19679_1,
        caseReviewStatusLastModifiedDate: '2019-01-01T01:00:00.000Z',
      },
    },
    familyTableState: {
      ...STATE_WITH_2_FAMILIES.familyTableState,
      familiesSortOrder: 'REVIEW_STATUS_CHANGED_DATE',
    },
  }
  const wrapper = renderTable(state)
  expect(wrapper.find('FamilyTableRow').map(content => content.prop('familyGuid'))).toEqual(['F011652_1', 'F011652_2'])
})

test('filters family table by search', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    familyTableState: { ...STATE_WITH_2_FAMILIES.familyTableState, familiesSearch: '1' },
    familyTableFilterState: {},
  }
  const wrapper = renderTable(state)
  const familyRows = wrapper.find('FamilyTableRow')
  expect(familyRows.length).toEqual(1)
  expect(familyRows.first().prop('familyGuid')).toEqual('F011652_1')
})

test('filters family table by filters', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    familyTableFilterState: { R0237_1000_genomes_demo: { savedVariants: ['Review'] } }
  }
  const wrapper = renderTable(state)
  const familyRows = wrapper.find('FamilyTableRow')
  expect(familyRows.length).toEqual(1)
  expect(familyRows.first().prop('familyGuid')).toEqual('F011652_1')
})

test('formats family export field values, including notes, firstSample, analysisStatus, assignedAnalyst, and analysedBy', () => {
  const state = cloneDeep(STATE_WITH_2_FAMILIES)
  state.familiesByGuid.F011652_1.analysisStatus = 'NOT_A_REAL_ANALYSIS_STATUS'
  state.familiesByGuid.F011652_1.assignedAnalyst = null
  state.familiesByGuid.F011652_1.analysedBy = []
  state.familiesByGuid.F011652_2.assignedAnalyst = { email: 'analyst@broadinstitute.org' }
  state.familiesByGuid.F011652_2.analysedBy = [
    { createdBy: 'user1', dataType: 'SNP', lastModifiedDate: '2020-01-01T01:00:00.000Z' },
    { createdBy: 'user2', dataType: 'SV', lastModifiedDate: '2021-01-01T01:00:00.000Z' },
  ]

  const wrapper = renderTable(state)
  const popupWrapper = shallow( wrapper.find('Popup[on="click"]').prop('content'))
  const exportUrls = popupWrapper.root().prop('downloads')

  const familiesExport = exportUrls.find(({ name }) => name === 'Families')
  const familiesData = familiesExport.getRawData(state)

  const family1 = familiesData.find(f => f.familyGuid === 'F011652_1')
  const family2 = familiesData.find(f => f.familyGuid === 'F011652_2')

  const [
    , , , firstSample1, , analysisStatus1, assignedAnalyst1, analysedBy1, analysisNotes1,
  ] = familiesExport.processRow(family1)
  const [
    , , , firstSample2, , , assignedAnalyst2, analysedBy2, analysisNotes2,
  ] = familiesExport.processRow(family2)

  // firstSample is absent for F011652_1 (no loaded dataset) and present for F011652_2
  expect(firstSample1).toBeUndefined()
  expect(firstSample2).toEqual('2018-03-13')

  // analysisStatus falls back to {}.name when missing from the lookup
  expect(analysisStatus1).toBeUndefined()

  // assignedAnalyst is formatted to an email when present, and to '' when null
  expect(assignedAnalyst1).toEqual('')
  expect(assignedAnalyst2).toEqual('analyst@broadinstitute.org')

  // analysedBy joins createdBy values for multiple entries
  expect(analysedBy1).toEqual('')
  expect(analysedBy2).toEqual('user1,user2')

  // analysisNotes is absent for F011652_1 and present (formatted) for F011652_2
  expect(analysisNotes1).toEqual('')
  expect(analysisNotes2).toEqual('A note;Another note')
})
