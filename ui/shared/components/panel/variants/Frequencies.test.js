import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import Frequencies from './Frequencies'
import { VARIANT, SV_VARIANT, STATE1 } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)
  shallow(<Frequencies store={store} variant={VARIANT} />)
  shallow(<Frequencies store={store} variant={SV_VARIANT} />)
})
