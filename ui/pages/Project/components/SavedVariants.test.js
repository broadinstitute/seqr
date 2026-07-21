import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'

import UpdateButton from 'shared/components/buttons/UpdateButton'
import { updateVariantTags } from 'redux/rootReducer'
import RoutedSavedVariants from './SavedVariants'
import VariantTagTypeBar from './VariantTagTypeBar'
import SelectSavedVariantsTable from './SelectSavedVariantsTable'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

jest.mock('../reducers', () => ({
  ...jest.requireActual('../reducers'),
  loadSavedVariants: () => ({ type: 'NOOP' }),
  loadFamilySavedVariants: () => ({ type: 'NOOP' }),
}))

jest.mock('redux/rootReducer', () => ({
  ...jest.requireActual('redux/rootReducer'),
  updateVariantTags: jest.fn(() => ({ type: 'NOOP' })),
}))

let mockLatestProps = null

// The shared SavedVariants panel renders the full variant review UI (annotations, predictions,
// individual genotypes, etc.) - a large, separately-owned/tested component. Double it here so this
// test can focus on the Project-level wrapper's own logic: tag options, filters, and routing.
jest.mock('shared/components/panel/variants/SavedVariants', () => function MockSavedVariants(props) {
  mockLatestProps = props
  const { tagOptions, selectedTag, filters, additionalFilter } = props
  const savedByField = filters.find(f => f.name === 'savedBy')
  return (
    <div className="mock-saved-variants">
      <div className="tag-options">{tagOptions.map(o => o.text || o.value).join(',')}</div>
      <div className="selected-tag">{selectedTag}</div>
      <div className="filter-names">{filters.map(f => f.name).join(',')}</div>
      <div className="additional-filter">{additionalFilter}</div>
      {savedByField && <div className="saved-by-filter"><savedByField.component /></div>}
    </div>
  )
})

configure({ adapter: new Adapter() })

test('renders tag options built from the project variant tag types, grouped by category', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
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
  const store = configureStore()(STATE_WITH_2_FAMILIES)
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
  const store = configureStore()(STATE_WITH_2_FAMILIES)
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
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/family/F011652_1']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>
  )

  expect(wrapper.find('.additional-filter').text()).toContain('Link Variants')
})

test('renders no link-variants button when there is no family route', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>
  )

  expect(wrapper.find('.additional-filter').text()).toEqual('')
})

test('renders the savedBy filter dropdown with options built from the project state', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>
  )

  expect(wrapper.find('.saved-by-filter').exists()).toBe(true)
})

test('getUpdateTagUrl updates the category filter and omits the tag segment for a category', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>
  )

  const url = mockLatestProps.getUpdateTagUrl('CMG Discovery Tags')

  expect(url).toEqual('/project/R0237_1000_genomes_demo/saved_variants')
  expect(store.getActions()).toContainEqual(
    { type: 'UPDATE_VARIANT_STATE', updates: { categoryFilter: 'CMG Discovery Tags' } },
  )
})

test('getUpdateTagUrl clears the category filter and includes the tag segment for a non-category tag', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/family/F011652_1']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>
  )

  const url = mockLatestProps.getUpdateTagUrl('Excluded')

  expect(url).toEqual('/project/R0237_1000_genomes_demo/saved_variants/family/F011652_1/Excluded')
  expect(store.getActions()).toContainEqual(
    { type: 'UPDATE_VARIANT_STATE', updates: { categoryFilter: null } },
  )
})

test('loadVariants resets the page and only reloads when the initial load or the family selection changes', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/family/F011652_1']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>
  )

  const { match } = mockLatestProps

  // initial load: newParams is the same object reference as match.params
  mockLatestProps.loadVariants(match.params)
  expect(store.getActions().filter(a => a.type === 'NOOP').length).toEqual(1)
  expect(store.getActions()).toContainEqual({ type: 'UPDATE_VARIANT_STATE', updates: { page: 1 } })

  // unchanged family selection, new object reference: page resets but no reload
  mockLatestProps.loadVariants({ ...match.params })
  expect(store.getActions().filter(a => a.type === 'NOOP').length).toEqual(1)

  // changed family selection: reloads
  mockLatestProps.loadVariants({ ...match.params, familyGuid: 'F011652_2' })
  expect(store.getActions().filter(a => a.type === 'NOOP').length).toEqual(2)
})

test('tableSummaryComponent renders the tag type bar and excludes tags based on the hide filters', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>
  )

  const renderSummary = props => mount(
    <Provider store={store}>
      <MemoryRouter>{mockLatestProps.tableSummaryComponent(props)}</MemoryRouter>
    </Provider>,
  )

  expect(renderSummary({ hideExcluded: false, hideReviewOnly: false }).find(VariantTagTypeBar).prop('excludeItems'))
    .toBeUndefined()
  expect(renderSummary({ hideExcluded: false, hideReviewOnly: true }).find(VariantTagTypeBar).prop('excludeItems'))
    .toEqual(['Review'])
  expect(renderSummary({ hideExcluded: true, hideReviewOnly: false }).find(VariantTagTypeBar).prop('excludeItems'))
    .toEqual(['Excluded'])
  expect(renderSummary({ hideExcluded: true, hideReviewOnly: true }).find(VariantTagTypeBar).prop('excludeItems'))
    .toEqual(['Excluded', 'Review'])
})

test('the link-variants form submits the selected variant guids and tags for the family', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/family/F011652_1']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>
  )

  const { onSubmit } = wrapper.find(UpdateButton).props()
  onSubmit({
    tags: [{ name: 'Review' }],
    variantGuids: { SV0000004_116042722_r0390_1000: true, SV0000002_1248367227_r0390_100: false },
  })

  expect(updateVariantTags).toHaveBeenCalledWith({
    tags: [{ name: 'Review' }],
    variantGuids: 'SV0000004_116042722_r0390_1000',
    familyGuid: 'F011652_1',
  })
})

test('renders the link-variants form fields when the modal is open', () => {
  const store = configureStore([thunk])({
    ...STATE_WITH_2_FAMILIES,
    modal: { 'F011652_1-linkVariants': { open: true } },
  })
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/family/F011652_1']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>
  )

  expect(wrapper.find(SelectSavedVariantsTable).exists()).toBe(true)
  expect(wrapper.find('table').exists()).toBe(true)
})
