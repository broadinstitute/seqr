import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter, Route } from 'react-router-dom'

import FamilyPage, { FamilyDetail } from './FamilyPage'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

const INITIAL_ENTRIES = ['/project/R0237_1000_genomes_demo/family_page/F011652_1']

test('renders the family display name and its individuals', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={INITIAL_ENTRIES}>
        <Route path="/project/:projectGuid/family_page/:familyGuid" component={FamilyPage} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('IndividualRow').length).toEqual(3)
})

test('renders discovery genes and disables search when data is not loaded, with no workspace loading message', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    familiesByGuid: {
      ...STATE_WITH_2_FAMILIES.familiesByGuid,
      F011652_1: {
        ...STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1,
        discoveryGeneIds: ['ENSG00000228198', 'ENSG00000164458', 'ENSG00000228198', 'ENSG00000UNKNOWN'],
      },
    },
    projectsByGuid: {
      ...STATE_WITH_2_FAMILIES.projectsByGuid,
      R0237_1000_genomes_demo: {
        ...STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo,
        workspaceName: undefined,
      },
    },
    familyTagTypeCounts: {},
  }
  const store = configureStore(state)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={INITIAL_ENTRIES}>
        <Route path="/project/:projectGuid/family_page/:familyGuid" component={FamilyPage} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.text()).toContain('Discovery Genes:')
  expect(wrapper.text()).toContain('OR2M3, TBXT')
  const popups = wrapper.find('Popup').filterWhere(p => typeof p.prop('content') === 'string')
  expect(popups.at(0).prop('content')).toEqual('Search is disabled until data is loaded')
})

test('renders no discovery genes when none match known genes', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    familiesByGuid: {
      ...STATE_WITH_2_FAMILIES.familiesByGuid,
      F011652_1: {
        ...STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1,
        discoveryGeneIds: ['ENSG00000UNKNOWN'],
      },
    },
  }
  const store = configureStore(state)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={INITIAL_ENTRIES}>
        <Route path="/project/:projectGuid/family_page/:familyGuid" component={FamilyPage} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.text()).not.toContain('Discovery Genes:')
})

test('renders compact family detail without variant details or expanded content', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={INITIAL_ENTRIES}>
        <FamilyDetail familyGuid="F011652_1" compact showVariantDetails={false} fields={[]} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('ExpandedFamily').length).toEqual(0)
  expect(wrapper.find('VariantDetail').length).toEqual(0)
})
