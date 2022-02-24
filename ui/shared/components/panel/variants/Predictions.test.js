import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'

import { getUser } from 'redux/selectors'
import Predictions from './Predictions'
import { STATE1, VARIANT, SV_VARIANT } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<Predictions store={store} variant={VARIANT} />)
  shallow(<Predictions store={store} variant={SV_VARIANT} />)
})
