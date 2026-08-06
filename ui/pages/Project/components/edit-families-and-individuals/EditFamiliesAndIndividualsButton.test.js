import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import EditFamiliesAndIndividualsButton from './EditFamiliesAndIndividualsButton'
import { STATE_WITH_2_FAMILIES } from '../../fixtures'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

test('renders a trigger button', () => {
  const store = configureStore({ ...STATE_WITH_2_FAMILIES, modal: {} })
  const wrapper = mount(
    <Provider store={store}>
      <EditFamiliesAndIndividualsButton />
    </Provider>,
  )

  expect(wrapper.text()).toEqual('Edit Families & Individuals')
})

test('shows the standard edit panes, without a Gregor import pane, by default', () => {
  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    modal: { editFamiliesAndIndividuals: { open: true } },
  })
  const wrapper = mount(
    <Provider store={store}>
      <EditFamiliesAndIndividualsButton />
    </Provider>,
  )

  const menuItems = wrapper.find('Tab').prop('panes').map(p => p.menuItem)
  expect(menuItems).toEqual([
    'Edit Families', 'Edit Individuals', 'Bulk Edit Families', 'Bulk Edit Individuals', 'Bulk Edit Individual Metadata',
  ])
})

test('shows the standard edit panes when there is no current project', () => {
  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    modal: { editFamiliesAndIndividuals: { open: true } },
    projectsByGuid: {},
  })
  const wrapper = mount(
    <Provider store={store}>
      <EditFamiliesAndIndividualsButton />
    </Provider>,
  )

  const menuItems = wrapper.find('Tab').prop('panes').map(p => p.menuItem)
  expect(menuItems).toEqual([
    'Edit Families', 'Edit Individuals', 'Bulk Edit Families', 'Bulk Edit Individuals', 'Bulk Edit Individual Metadata',
  ])
})

test('adds a Gregor import pane when the project has a Gregor finding tag type', () => {
  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    modal: { editFamiliesAndIndividuals: { open: true } },
    projectsByGuid: {
      ...STATE_WITH_2_FAMILIES.projectsByGuid,
      R0237_1000_genomes_demo: {
        ...STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo,
        variantTagTypes: [{ name: 'GREGoR Finding' }],
      },
    },
  })
  const wrapper = mount(
    <Provider store={store}>
      <EditFamiliesAndIndividualsButton />
    </Provider>,
  )

  const menuItems = wrapper.find('Tab').prop('panes').map(p => p.menuItem)
  expect(menuItems).toContain('Import From Gregor Metadata')
  expect(menuItems.length).toEqual(6)
})
