import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import { GeneLists, AddGeneListsButton } from './GeneLists'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

// Loading is triggered on mount via a thunk action creator; replace it with a no-op so mounting
// does not attempt to make a real HTTP request or require additional reducer STATE_WITH_2_FAMILIES
jest.mock('../reducers', () => ({
  ...jest.requireActual('../reducers'),
  loadProjectLocusLists: () => ({ type: 'NOOP' }),
  updateLocusLists: values => ({ type: 'UPDATE_LOCUS_LISTS', ...values }),
}))

configure({ adapter: new Adapter() })

test('renders gene lists for the current project', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <GeneLists />
    </Provider>
  )

  expect(wrapper.find('ButtonLink').at(0).text()).toEqual('Known Genes')
})

test('shows a loading indicator while gene lists are loading', () => {
  const loadingState = { ...STATE_WITH_2_FAMILIES, projectLocusListsLoading: { isLoading: true } }
  const store = configureStore()(loadingState)
  const wrapper = mount(
    <Provider store={store}>
      <GeneLists />
    </Provider>
  )

  expect(wrapper.find('Dimmer').prop('active')).toBe(true)
  expect(wrapper.text()).toContain('Loading')
})

test('dispatches an update when a gene list is removed', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <GeneLists />
    </Provider>
  )

  wrapper.find('DispatchRequestButton').prop('onSubmit')()

  const actions = store.getActions()
  const updateAction = actions.find(action => action.type === 'UPDATE_LOCUS_LISTS')
  expect(updateAction.locusListGuids).toEqual(['LL00001_locus_list'])
  expect(updateAction.delete).toBe(true)
})

test('renders no gene lists when the project has no locusListGuids', () => {
  const stateWithNoLists = {
    ...STATE_WITH_2_FAMILIES,
    projectsByGuid: {
      ...STATE_WITH_2_FAMILIES.projectsByGuid,
      R0237_1000_genomes_demo: {
        ...STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo,
        locusListGuids: undefined,
      },
    },
  }
  const store = configureStore()(stateWithNoLists)
  const wrapper = mount(
    <Provider store={store}>
      <GeneLists />
    </Provider>
  )

  expect(wrapper.find('GeneLists__ItemContainer').length).toBe(0)
  expect(wrapper.find('ButtonLink').filterWhere(n => n.text() === 'Show More...').length).toBe(0)
})

test('shows a "Show More" link when there are more than 20 gene lists', () => {
  const manyLocusListGuids = Array.from({ length: 25 }, (v, i) => `LL${i}_locus_list`)
  const stateWithManyLists = {
    ...STATE_WITH_2_FAMILIES,
    projectsByGuid: {
      ...STATE_WITH_2_FAMILIES.projectsByGuid,
      R0237_1000_genomes_demo: {
        ...STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo,
        locusListGuids: manyLocusListGuids,
      },
    },
    locusListsByGuid: manyLocusListGuids.reduce((acc, locusListGuid, i) => ({
      ...acc,
      [locusListGuid]: { locusListGuid, name: `Gene List ${i}`, description: '', numEntries: 1 },
    }), {}),
  }
  const store = configureStore()(stateWithManyLists)
  const wrapper = mount(
    <Provider store={store}>
      <GeneLists />
    </Provider>
  )

  expect(wrapper.find('GeneLists__ItemContainer').length).toBe(20)
  const showMore = wrapper.find('ButtonLink').filterWhere(n => n.text() === 'Show More...')
  expect(showMore.length).toBe(1)

  showMore.first().simulate('click')
  wrapper.update()

  expect(wrapper.find('GeneLists__ItemContainer').length).toBe(25)
  expect(wrapper.find('ButtonLink').filterWhere(n => n.text() === 'Show More...').length).toBe(0)
})

test('renders the add gene lists button and modal form', () => {
  const stateWithOpenModal = {
    ...STATE_WITH_2_FAMILIES,
    modal: { 'add-gene-list-R0237_1000_genomes_demo': { open: true } },
  }
  const store = configureStore([thunk])(stateWithOpenModal)
  const wrapper = mount(
    <Provider store={store}>
      <AddGeneListsButton />
    </Provider>
  )

  expect(wrapper.text()).toContain('Add an existing Gene List to 1000 Genomes Demo or')
  expect(wrapper.find('button').filterWhere(n => n.text() === 'Create New Gene List').length).toBe(1)

  const field = wrapper.find('ForwardRef(Field)[name="locusListGuids"]')

  expect(field.prop('parse')({ LL1: true, LL2: false })).toEqual(['LL1'])
  expect(field.prop('parse')(undefined)).toEqual([])
  expect(field.prop('format')(['LL1', 'LL2'])).toEqual({ LL1: true, LL2: true })
  expect(field.prop('format')(undefined)).toEqual({})
})
