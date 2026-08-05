import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'
import { STATE_WITH_2_FAMILIES } from 'pages/Project/fixtures'
import CreateVariantButton from './CreateVariantButton'

configure({ adapter: new Adapter() })

test('renders add manual variant and SV buttons for a family', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const family = STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1

  const wrapper = mount(
    <Provider store={store}>
      <CreateVariantButton family={family} />
    </Provider>,
  )

  const buttonTexts = wrapper.find('ButtonLink').map(button => button.prop('content'))
  expect(buttonTexts).toEqual(['Add Manual Variant', 'Add Manual SV'])
})
