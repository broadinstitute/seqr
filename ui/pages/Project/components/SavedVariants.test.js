import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import cloneDeep from 'lodash/cloneDeep'

import UpdateButton from 'shared/components/buttons/UpdateButton'
import { updateVariantTags } from 'redux/rootReducer'
import { REQUEST_SAVED_VARIANTS } from 'redux/utils/reducerUtils'
import { mockFetchResponse, mockFetchRejection, flushAll, getLastFetchUrl } from 'shared/utils/testHelpers'
import { MME_TAG_NAME } from 'shared/utils/constants'
import RoutedSavedVariants from './SavedVariants'
import VariantTagTypeBar from './VariantTagTypeBar'
import SelectSavedVariantsTable from './SelectSavedVariantsTable'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

const getLinkVariantsValidate = (wrapper) => {
  const { formFields } = wrapper.find(UpdateButton).props()
  return formFields.find(f => f.name === 'variantGuids').validate
}

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
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('.tag-options').text().split(',')).toEqual([
    'All Saved', 'Collaboration', 'Review', 'Excluded', 'CMG Discovery Tags', 'Tier 1 - Phenotype not delineated',
  ])
})

test('defaults to the "Show All" tag when there is no tag/variant in the route', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('.selected-tag').text()).toEqual('ALL')
})

test('uses the requested tag from the route', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/Excluded']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('.selected-tag').text()).toEqual('Excluded')
})

test('renders a link-variants button for a family route when the project is editable', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/family/F011652_1']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('.additional-filter').text()).toContain('Link Variants')
})

test('renders no link-variants button when there is no family route', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('.additional-filter').text()).toEqual('')
})

test('renders the savedBy filter dropdown with options built from the project state', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('.saved-by-filter').exists()).toBe(true)
})

test('getUpdateTagUrl updates the category filter and omits the tag segment for a category', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  const url = mockLatestProps.getUpdateTagUrl('CMG Discovery Tags')

  expect(url).toEqual('/project/R0237_1000_genomes_demo/saved_variants')
  expect(store.getActions()).toContainEqual(
    { type: 'UPDATE_VARIANT_STATE', updates: { categoryFilter: 'CMG Discovery Tags' } },
  )
})

test('getUpdateTagUrl clears the category filter and includes the tag segment for a non-category tag', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/family/F011652_1']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  const url = mockLatestProps.getUpdateTagUrl('Excluded')

  expect(url).toEqual('/project/R0237_1000_genomes_demo/saved_variants/family/F011652_1/Excluded')
  expect(store.getActions()).toContainEqual(
    { type: 'UPDATE_VARIANT_STATE', updates: { categoryFilter: null } },
  )
})

test('loadVariants resets the page and only reloads when the initial load or the family selection changes', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/family/F011652_1']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  const { match } = mockLatestProps

  // initial load: newParams is the same object reference as match.params
  mockLatestProps.loadVariants(match.params)
  expect(store.getActions().filter(a => a.type === REQUEST_SAVED_VARIANTS).length).toEqual(1)
  expect(store.getActions()).toContainEqual({ type: 'UPDATE_VARIANT_STATE', updates: { page: 1 } })

  // unchanged family selection, new object reference: page resets but no reload
  mockLatestProps.loadVariants({ ...match.params })
  expect(store.getActions().filter(a => a.type === REQUEST_SAVED_VARIANTS).length).toEqual(1)

  // changed family selection: reloads
  mockLatestProps.loadVariants({ ...match.params, familyGuid: 'F011652_2' })
  expect(store.getActions().filter(a => a.type === REQUEST_SAVED_VARIANTS).length).toEqual(2)
})

test('tableSummaryComponent renders the tag type bar and excludes tags based on the hide filters', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
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
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/family/F011652_1']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
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
    </Provider>,
  )

  expect(wrapper.find(SelectSavedVariantsTable).exists()).toBe(true)
  expect(wrapper.find('table').exists()).toBe(true)
})

test('the link-variants form validation requires 2+ variants in the same gene', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/family/F011652_1']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  const validate = getLinkVariantsValidate(wrapper)

  expect(validate({})).toEqual('Multiple variants required')
  expect(validate({ v1: { transcripts: { GENE1: [{}] } } })).toEqual('Multiple variants required')

  expect(validate({
    v1: { transcripts: { GENE1: [{}] } },
    v2: { transcripts: { GENE2: [{}] } },
  })).toEqual('Compound het pairs must be in the same gene')

  expect(validate({
    v1: { transcripts: { GENE1: [{}] } },
    v2: { transcripts: { GENE1: [{}] } },
  })).toBeUndefined()

  expect(validate({
    v1: { transcripts: { GENE1: [{}] } },
    v2: { transcripts: { GENE1: [{}] } },
    v3: { transcripts: { GENE1: [{}] } },
  })).toBeUndefined()
})

test('loadVariants uses the analysis group families when there is no family in the route', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  const { match } = mockLatestProps

  expect(() => mockLatestProps.loadVariants(match.params)).not.toThrow()
  expect(store.getActions()).toContainEqual({ type: 'UPDATE_VARIANT_STATE', updates: { page: 1 } })
})

test('tagOptions omits the category header for tags with no category and falls back when there are no tag types', () => {
  const noCategoryState = {
    ...STATE_WITH_2_FAMILIES,
    projectsByGuid: {
      ...STATE_WITH_2_FAMILIES.projectsByGuid,
      R0237_1000_genomes_demo: {
        ...STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo,
        variantTagTypes: [
          { name: 'Review', category: 'Collaboration', color: '#668FE3', variantTagTypeGuid: 'VTT_REVIEW', numTags: 2 },
          { name: 'Uncategorized', category: null, color: '#000000', variantTagTypeGuid: 'VTT_NONE', numTags: 0 },
        ],
      },
    },
  }
  const store = configureStore([thunk])(noCategoryState)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('.tag-options').text().split(',')).toEqual(['All Saved', 'Collaboration', 'Review', 'Uncategorized'])

  const noTagTypesState = {
    ...STATE_WITH_2_FAMILIES,
    projectsByGuid: {
      ...STATE_WITH_2_FAMILIES.projectsByGuid,
      R0237_1000_genomes_demo: {
        ...STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo,
        variantTagTypes: null,
      },
    },
  }
  const noTagTypesStore = configureStore([thunk])(noTagTypesState)
  const noTagTypesWrapper = mount(
    <Provider store={noTagTypesStore}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  expect(noTagTypesWrapper.find('.tag-options').text().split(',')).toEqual(['All Saved'])
})

test('selects no tag when a specific variant is requested from the route', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter
        initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/variant/SV0000004_116042722_r0390_1000']}
      >
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('.selected-tag').text()).toEqual('')
})

test('includes the hideKnownGeneForPhenotype filter for the discovery tag category', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/CMG%20Discovery%20Tags']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('.filter-names').text().split(',')).toContain('hideKnownGeneForPhenotype')
})

test('loadVariants requests a single variant by guid when it is not already loaded', async () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  mount(
    <Provider store={store}>
      <MemoryRouter
        initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/variant/SV_NOT_LOADED']}
      >
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  mockLatestProps.loadVariants(mockLatestProps.match.params)
  await flushAll()

  expect(getLastFetchUrl()).toContain('/api/project/R0237_1000_genomes_demo/saved_variants/SV_NOT_LOADED?')
})

test('loadVariants does not re-request a single variant that is already loaded', async () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  mount(
    <Provider store={store}>
      <MemoryRouter
        initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/variant/SV0000004_116042722_r0390_1000']}
      >
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  mockLatestProps.loadVariants(mockLatestProps.match.params)
  await flushAll()

  expect(fetch).not.toHaveBeenCalled()
})

test('loadVariants does not re-request families whose saved variants are already loaded', async () => {
  const loadedState = {
    ...STATE_WITH_2_FAMILIES,
    savedVariantFamilies: { F011652_1: { loaded: true, noteVariants: true } },
  }
  const store = configureStore([thunk])(loadedState)
  mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/family/F011652_1']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  mockLatestProps.loadVariants(mockLatestProps.match.params)
  await flushAll()

  expect(fetch).not.toHaveBeenCalled()
})

test('loadVariants requests note variants for the "Has Notes" tag', async () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/Has%20Notes']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  mockLatestProps.loadVariants(mockLatestProps.match.params)
  await flushAll()

  expect(getLastFetchUrl()).toContain('/api/project/R0237_1000_genomes_demo/saved_variants?')
  expect(getLastFetchUrl()).toContain('includeNoteVariants=true')
})

test('receiving a single-variant response marks its families as loaded', async () => {
  mockFetchResponse({ familiesByGuid: { F011652_1: {} }, savedVariantsByGuid: {} })
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  mount(
    <Provider store={store}>
      <MemoryRouter
        initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/variant/SV_NOT_LOADED']}
      >
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  mockLatestProps.loadVariants(mockLatestProps.match.params)
  await flushAll()

  expect(store.getActions()).toContainEqual(
    expect.objectContaining({ updates: { F011652_1: { loaded: true, noteVariants: undefined } } }),
  )
})

test('loadVariants does not re-request already-loaded families derived from the project when there is no route family/analysis group', async () => {
  const loadedFamiliesState = {
    ...STATE_WITH_2_FAMILIES,
    projectsByGuid: {
      ...STATE_WITH_2_FAMILIES.projectsByGuid,
      R0237_1000_genomes_demo: {
        ...STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo,
        familiesLoaded: true,
      },
    },
    savedVariantFamilies: {
      F011652_1: { loaded: true, noteVariants: false },
      F011652_2: { loaded: true, noteVariants: false },
    },
  }
  const store = configureStore([thunk])(loadedFamiliesState)
  mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  mockLatestProps.loadVariants(mockLatestProps.match.params)
  await flushAll()

  expect(fetch).not.toHaveBeenCalled()
})

test('dispatches an error action when the saved variants request fails', async () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  mockFetchRejection(new Error('saved variants request failed'))

  mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/family/F011652_1']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  mockLatestProps.loadVariants(mockLatestProps.match.params)
  await flushAll()

  expect(store.getActions()).toContainEqual(
    expect.objectContaining({ type: 'RECEIVE_DATA', error: 'saved variants request failed' }),
  )
})

test('getSavedVariantTagTypeCountsByFamily counts mme submissions and de-dupes repeated tag names on a variant', () => {
  const mmeTagState = cloneDeep(STATE_WITH_2_FAMILIES)
  mmeTagState.savedVariantsByGuid.SV0000004_116042722_r0390_1000.mmeSubmissions = [{ submissionGuid: 'MS1' }]
  mmeTagState.savedVariantsByGuid.SV0000004_116042722_r0390_1000.tagGuids.push('VT1726942_1248367227_r0390_101_dup')
  mmeTagState.variantTagsByGuid.VT1726942_1248367227_r0390_101_dup = {
    ...mmeTagState.variantTagsByGuid.VT1726942_1248367227_r0390_101,
    tagGuid: 'VT1726942_1248367227_r0390_101_dup',
  }

  const store = configureStore([thunk])(mmeTagState)
  mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants/family/F011652_1']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  expect(mockLatestProps.tagTypeCounts[MME_TAG_NAME]).toEqual(1)
  expect(mockLatestProps.tagTypeCounts.Review).toEqual(3)
})

test('saved variant options handles a family with no saved variants', () => {
  const noVariantsState = cloneDeep(STATE_WITH_2_FAMILIES)
  noVariantsState.familiesByGuid.F_NO_VARIANTS = {
    ...noVariantsState.familiesByGuid.F011652_1,
    familyGuid: 'F_NO_VARIANTS',
  }

  const store = configureStore([thunk])(noVariantsState)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={['/project/R0237_1000_genomes_demo/saved_variants']}>
        <RoutedSavedVariants match={{ url: '/project/R0237_1000_genomes_demo/saved_variants' }} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('.saved-by-filter').exists()).toBe(true)
})
