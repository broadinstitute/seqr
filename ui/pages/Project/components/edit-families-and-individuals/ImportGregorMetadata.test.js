import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import ImportGregorMetadata from './ImportGregorMetadata'
import { ANVIL_FIELDS } from 'shared/utils/constants'
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
    </Provider>
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
    </Provider>
  )

  expect(wrapper.text()).toContain('Imported 3 individuals')
  expect(wrapper.text()).toContain('2 individuals were skipped')
})
