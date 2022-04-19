import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'

import VariantIndividuals from './VariantIndividuals'
import { STATE1, VARIANT, SV_VARIANT } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<VariantIndividuals familyGuid="F011652_1" store={store} variant={VARIANT} />)
  shallow(<VariantIndividuals familyGuid="F011652_1" store={store} variant={SV_VARIANT} />)
})
