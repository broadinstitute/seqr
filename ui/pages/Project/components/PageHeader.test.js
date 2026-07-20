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
