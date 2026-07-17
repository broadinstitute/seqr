import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'

import { GeneLists } from './GeneLists'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

// Loading is triggered on mount via a thunk action creator; replace it with a no-op so mounting
// does not attempt to make a real HTTP request or require additional reducer state
jest.mock('../reducers', () => ({
  ...jest.requireActual('../reducers'),
  loadProjectLocusLists: () => ({ type: 'NOOP' }),
}))

configure({ adapter: new Adapter() })

const STATE = {
  ...STATE_WITH_2_FAMILIES,
  modal: {},
  projectLocusListsLoading: { isLoading: false },
  projectsByGuid: {
    ...STATE_WITH_2_FAMILIES.projectsByGuid,
    R0237_1000_genomes_demo: {
      ...STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo,
      locusListGuids: ['LL00001_locus_list'],
    },
  },
  locusListsByGuid: {
    LL00001_locus_list: {
      locusListGuid: 'LL00001_locus_list',
      name: 'Known Genes',
      description: 'A list of known genes',
      numEntries: 5,
    },
  },
}

test('renders gene lists for the current project', () => {
  const store = configureStore()(STATE)
  const wrapper = mount(
    <Provider store={store}>
      <GeneLists />
    </Provider>
  )

  expect(wrapper.find('ButtonLink').at(0).text()).toEqual('Known Genes')
})

test('shows a loading indicator while gene lists are loading', () => {
  const loadingState = { ...STATE, projectLocusListsLoading: { isLoading: true } }
  const store = configureStore()(loadingState)
  const wrapper = mount(
    <Provider store={store}>
      <GeneLists />
    </Provider>
  )

  expect(wrapper.find('Dimmer').prop('active')).toBe(true)
  expect(wrapper.text()).toContain('Loading')
})
