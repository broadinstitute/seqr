import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import { ANVIL_FIELDS } from 'shared/utils/constants'
import { flushAll, getLastFetchUrl } from 'shared/utils/testHelpers'
import ImportGregorMetadata from './ImportGregorMetadata'
import { STATE_WITH_2_FAMILIES } from '../../fixtures'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

test('renders the description and AnVIL workspace fields', () => {
  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    importStats: { gregorMetadata: {} },
  })
  const wrapper = mount(
    <Provider store={store}>
      <ImportGregorMetadata />
    </Provider>,
  )

  expect(wrapper.text()).toContain('Import individuals and their metadata from the specified workspace')
  ANVIL_FIELDS.forEach((field) => {
    expect(wrapper.text()).toContain(field.label)
  })
  expect(wrapper.find('Message').exists()).toBe(false)
})

test('shows info and warning messages from a previous import', () => {
  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    importStats: {
      gregorMetadata: { info: ['Imported 3 individuals'], warnings: ['2 individuals were skipped'] },
    },
  })
  const wrapper = mount(
    <Provider store={store}>
      <ImportGregorMetadata />
    </Provider>,
  )

  expect(wrapper.text()).toContain('Imported 3 individuals')
  expect(wrapper.text()).toContain('2 individuals were skipped')
})

test('submits the workspace metadata import form', async () => {
  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    importStats: { gregorMetadata: {} },
  })
  const wrapper = mount(
    <Provider store={store}>
      <ImportGregorMetadata />
    </Provider>,
  )

  await wrapper.find('FormWrapper').prop('onSubmit')({ workspaceNamespace: 'ns', workspaceName: 'ws' })
  await flushAll()

  expect(getLastFetchUrl()).toEqual(
    `/api/project/${STATE_WITH_2_FAMILIES.currentProjectGuid}/import_gregor_metadata`,
  )
})
