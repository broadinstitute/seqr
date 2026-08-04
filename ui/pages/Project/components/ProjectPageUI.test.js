import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import cloneDeep from 'lodash/cloneDeep'
import ProjectPageUI from './ProjectPageUI'

import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

const MATCH = { params: {} }

test('renders the project sections and the families table', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <ProjectPageUI match={MATCH} />
      </MemoryRouter>
    </Provider>,
  )

  const sectionHeaders = wrapper.find('StyledComponents__SectionHeader').map(header => header.text())
  expect(sectionHeaders).toEqual([
    'Analysis Groups', 'Access Groups', 'Gene Lists', 'Overview', 'Variant Tags', 'Notifications', 'Collaborators', 'Families',
  ])
  expect(wrapper.find('FamilyTableRow').length).toEqual(2)
})

test('renders an analysis group page without an edit button or notifications section', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <ProjectPageUI match={{ params: { analysisGroupGuid: 'AG0000183_test_group' } }} />
      </MemoryRouter>
    </Provider>,
  )

  const sectionHeaders = wrapper.find('StyledComponents__SectionHeader').map(header => header.text())
  expect(sectionHeaders).toEqual([
    'Analysis Group', 'Gene Lists', 'Overview', 'Variant Tags', 'Collaborators', 'Families',
  ])
  expect(wrapper.find('Link').someWhere(
    link => link.prop('to') === '/project/R0237_1000_genomes_demo/saved_variants/analysis_group/AG0000183_test_group',
  )).toBe(true)
})

test('renders a loader instead of section content when project data is loading', () => {
  const state = cloneDeep(STATE_WITH_2_FAMILIES)
  state.projectDetailsLoading = { isLoading: true }
  state.projectOverviewLoading = { isLoading: true }
  const store = configureStore(state)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <ProjectPageUI match={MATCH} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('Loader').length).toBeGreaterThan(0)
})

test('does not render an edit button when the user cannot edit the project', () => {
  const state = cloneDeep(STATE_WITH_2_FAMILIES)
  state.projectsByGuid.R0237_1000_genomes_demo.canEdit = false
  const store = configureStore(state)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <ProjectPageUI match={MATCH} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('UpdateAnalysisGroupButton').length).toEqual(0)
})
