import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'

import PageHeader from './PageHeader'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const renderPageHeader = props => mount(
  <Provider store={configureStore()(STATE_WITH_2_FAMILIES)}>
    <MemoryRouter>
      <PageHeader {...props} />
    </MemoryRouter>
  </Provider>,
)

test('renders the project title and an edit button on the project page', () => {
  const wrapper = renderPageHeader({ match: { params: { breadcrumb: 'project_page' } } })

  expect(wrapper.find('Breadcrumb').text()).toContain('1000 Genomes Demo')
  expect(wrapper.find('ButtonLink[content="Edit Project"]').exists()).toBe(true)
})

test('renders the analysis group name in the breadcrumb', () => {
  const wrapper = renderPageHeader({
    match: { url: '/project/R0237_1000_genomes_demo/analysis_group/AG0000183_test_group', params: { breadcrumb: 'analysis_group', breadcrumbId: 'AG0000183_test_group' } },
  })

  expect(wrapper.find('Breadcrumb').text()).toContain('Analysis Group: Test Group')
})

test('renders the family description on the family page', () => {
  const wrapper = renderPageHeader({
    match: {
      url: '/project/R0237_1000_genomes_demo/family_page/F011652_1',
      params: { breadcrumb: 'family_page', breadcrumbId: 'F011652_1' },
    },
  })

  expect(wrapper.find('Breadcrumb').text()).toContain('Family: 1')
})

test('renders nothing when there is no current project', () => {
  const store = configureStore()({ ...STATE_WITH_2_FAMILIES, currentProjectGuid: null })
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <PageHeader match={{ params: { breadcrumb: 'project_page' } }} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('Breadcrumb').exists()).toBe(false)
})

test('renders the consent code when the user is a PM viewing a project with a consent code', () => {
  const store = configureStore()({
    ...STATE_WITH_2_FAMILIES,
    user: { ...STATE_WITH_2_FAMILIES.user, isPm: true },
  })
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <PageHeader match={{ params: { breadcrumb: 'project_page' } }} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.text()).toContain('Consent Code:')
})

test('renders the project title for an unrecognized breadcrumb', () => {
  const wrapper = renderPageHeader({ match: { params: { breadcrumb: 'other_page' } } })

  expect(wrapper.find('Breadcrumb').text()).toContain('1000 Genomes Demo')
  expect(wrapper.find('ButtonLink[content="Edit Project"]').exists()).toBe(false)
})

test('renders no description on the family page for the matchmaker exchange and rna-seq results sections', () => {
  const wrapper = renderPageHeader({
    match: {
      url: '/project/R0237_1000_genomes_demo/family_page/F011652_1/matchmaker_exchange',
      params: { breadcrumb: 'family_page', breadcrumbId: 'F011652_1', breadcrumbIdSection: 'matchmaker_exchange' },
    },
  })

  expect(wrapper.find('Breadcrumb').text()).toContain('Family: 1')
  expect(wrapper.find('InlineHeader').exists()).toBe(false)
})
