import React from 'react'
import { shallow, mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import { FAMILY_MAIN_FIELDS, FAMILY_DETAIL_FIELDS } from 'shared/utils/constants'

import { flushAll } from 'shared/utils/testHelpers'
import FamilyTable from './FamilyTable'
import { STATE_WITH_2_FAMILIES } from '../../fixtures'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

test('toggles compact/full family details', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <FamilyTable
          detailFields={FAMILY_DETAIL_FIELDS}
          noDetailFields={FAMILY_MAIN_FIELDS}
        />
      </MemoryRouter>
    </Provider>,
  )

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
  const store = configureStore(loadingState)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <FamilyTable
          detailFields={FAMILY_DETAIL_FIELDS}
          noDetailFields={FAMILY_MAIN_FIELDS}
        />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('Loader').exists()).toBe(true)
  expect(wrapper.find('FamilyTableRow').length).toEqual(0)
})

test('renders an empty message when there are no visible families', () => {
  const emptyState = {
    ...STATE_WITH_2_FAMILIES,
    familiesByGuid: {},
  }
  const store = configureStore(emptyState)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <FamilyTable
          detailFields={FAMILY_DETAIL_FIELDS}
          noDetailFields={FAMILY_MAIN_FIELDS}
        />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('FamilyTableRow').length).toEqual(0)
  expect(wrapper.text()).toContain('0 families found')
})

test('loads export data when the export popup content is rendered', async () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <FamilyTable
          detailFields={FAMILY_DETAIL_FIELDS}
          noDetailFields={FAMILY_MAIN_FIELDS}
        />
      </MemoryRouter>
    </Provider>,
  )

  fetch.mockClear()

  // Popup content is a portal only rendered on hover/click, so render its `content` prop directly
  const popupContent = wrapper.find('Popup[on="click"]').prop('content')
  shallow(popupContent)
  await flushAll()

  const requestedUrls = fetch.mock.calls.map(([url]) => url)
  expect(requestedUrls.some(
    url => url.includes(`/api/project/${STATE_WITH_2_FAMILIES.currentProjectGuid}/get_individuals`),
  )).toBe(true)
  expect(requestedUrls.some(
    url => url.includes(`/api/project/${STATE_WITH_2_FAMILIES.currentProjectGuid}/get_family_notes`),
  )).toBe(true)
})
