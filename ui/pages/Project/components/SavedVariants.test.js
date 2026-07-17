import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'

import RoutedSavedVariants from './SavedVariants'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

jest.mock('../reducers', () => ({
  ...jest.requireActual('../reducers'),
  loadSavedVariants: () => ({ type: 'NOOP' }),
}))

// The shared SavedVariants panel renders the full variant review UI (annotations, predictions,
// individual genotypes, etc.) - a large, separately-owned/tested component. Double it here so this
// test can focus on the Project-level wrapper's own logic: tag options, filters, and routing.
jest.mock('shared/components/panel/variants/SavedVariants', () => function MockSavedVariants(
  { tagOptions, selectedTag, filters, additionalFilter },
) {
  return (
    <div className="mock-saved-variants">
      <div className="tag-options">{tagOptions.map(o => o.text || o.value).join(',')}</div>
      <div className="selected-tag">{selectedTag}</div>
      <div className="filter-names">{filters.map(f => f.name).join(',')}</div>
      <div className="additional-filter">{additionalFilter}</div>
    </div>
  )
})

configure({ adapter: new Adapter() })

const STATE = {
  ...STATE_WITH_2_FAMILIES,
  modal: {},
  savedVariantsLoading: { isLoading: false },
  projectsByGuid: {
    ...STATE_WITH_2_FAMILIES.projectsByGuid,
    R0237_1000_genomes_demo: {
      ...STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo,
      variantTagTypes: [
        { name: 'Review', category: 'Collaboration', color: '#668FE3' },
        { name: 'Excluded', category: 'Collaboration', color: '#668FE3' },
        { name: 'Tier 1 - Phenotype not delineated', category: 'CMG Discovery Tags', color: '#44AA60' },
      ],
    },
  },
}

test('renders tag options built from the project variant tag types, grouped by category', () => {
  const store = configureStore()(STATE)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>
  )

  expect(wrapper.find('.tag-options').text().split(',')).toEqual([
    'All Saved', 'Collaboration', 'Review', 'Excluded', 'CMG Discovery Tags', 'Tier 1 - Phenotype not delineated',
  ])
})

test('defaults to the "Show All" tag when there is no tag/variant in the route', () => {
  const store = configureStore()(STATE)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>
  )

  expect(wrapper.find('.selected-tag').text()).toEqual('ALL')
})

test('uses the requested tag from the route', () => {
  const store = configureStore()(STATE)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/Excluded']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>
  )

  expect(wrapper.find('.selected-tag').text()).toEqual('Excluded')
})

test('renders a link-variants button for a family route when the project is editable', () => {
  const store = configureStore()(STATE)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/family/F011652_1']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>
  )

  expect(wrapper.find('.additional-filter').text()).toContain('Link Variants')
})
