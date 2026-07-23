import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import EditIndividualMetadataButton from './EditIndividualMetadataButton'
import { INDIVIDUAL_ID_EXPORT_DATA } from 'shared/utils/constants'
import { STATE_WITH_2_FAMILIES } from '../../fixtures'

// jsdom does not implement createObjectURL; the bulk form's template download links need it
global.URL.createObjectURL = jest.fn()

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

test('renders a trigger button', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <EditIndividualMetadataButton />
    </Provider>
  )

  expect(wrapper.text()).toEqual('Bulk Edit Metadata')
})

test('shows the bulk edit metadata form when opened', () => {
  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    modal: { editIndividualsMetadata: { open: true } },
  })
  const wrapper = mount(
    <Provider store={store}>
      <EditIndividualMetadataButton />
    </Provider>
  )

  INDIVIDUAL_ID_EXPORT_DATA.forEach((field) => {
    expect(wrapper.text()).toContain(field.header)
  })
})
