import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import { getLastFetchUrl, getLastFetchOptions, getLastFetchBody, flushAll } from 'shared/utils/testHelpers'
import { GeneLists, AddGeneListsButton } from './GeneLists'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

test('renders gene lists for the current project', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <GeneLists />
    </Provider>,
  )

  expect(wrapper.find('ButtonLink').at(0).text()).toEqual('Known Genes')
})

test('shows a loading indicator while gene lists are loading', () => {
  const loadingState = { ...STATE_WITH_2_FAMILIES, projectLocusListsLoading: { isLoading: true } }
  const store = configureStore([thunk])(loadingState)
  const wrapper = mount(
    <Provider store={store}>
      <GeneLists />
    </Provider>,
  )

  expect(wrapper.find('Dimmer').prop('active')).toBe(true)
  expect(wrapper.text()).toContain('Loading')
})

test('dispatches an update when a gene list is removed', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <GeneLists />
    </Provider>,
  )

  wrapper.find('DispatchRequestButton').prop('onSubmit')()

  expect(getLastFetchUrl()).toEqual(`/api/project/${STATE_WITH_2_FAMILIES.currentProjectGuid}/delete_locus_lists`)
  expect(getLastFetchOptions().method).toEqual('POST')
  expect(getLastFetchBody()).toEqual({ locusListGuids: ['LL00001_locus_list'], delete: true })
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
  const store = configureStore([thunk])(stateWithNoLists)
  const wrapper = mount(
    <Provider store={store}>
      <GeneLists />
    </Provider>,
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
  const store = configureStore([thunk])(stateWithManyLists)
  const wrapper = mount(
    <Provider store={store}>
      <GeneLists />
    </Provider>,
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
    </Provider>,
  )

  expect(wrapper.text()).toContain('Add an existing Gene List to 1000 Genomes Demo or')
  expect(wrapper.find('button').filterWhere(n => n.text() === 'Create New Gene List').length).toBe(1)

  const field = wrapper.find('ForwardRef(Field)[name="locusListGuids"]')

  expect(field.prop('parse')({ LL1: true, LL2: false })).toEqual(['LL1'])
  expect(field.prop('parse')(undefined)).toEqual([])
  expect(field.prop('format')(['LL1', 'LL2'])).toEqual({ LL1: true, LL2: true })
  expect(field.prop('format')(undefined)).toEqual({})
})

test('submits the add gene lists form', async () => {
  const stateWithOpenModal = {
    ...STATE_WITH_2_FAMILIES,
    modal: { 'add-gene-list-R0237_1000_genomes_demo': { open: true } },
  }
  const store = configureStore([thunk])(stateWithOpenModal)
  const wrapper = mount(
    <Provider store={store}>
      <AddGeneListsButton />
    </Provider>,
  )

  wrapper.find('FormWrapper').prop('onSubmit')({ locusListGuids: ['LL00002_locus_list'] })
  await flushAll()

  expect(getLastFetchUrl()).toEqual(`/api/project/${STATE_WITH_2_FAMILIES.currentProjectGuid}/add_locus_lists`)
  expect(getLastFetchBody()).toEqual({ locusListGuids: ['LL00002_locus_list'] })
})
