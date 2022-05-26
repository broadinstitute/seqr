import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'

import GeneBreakdown from './GeneBreakdown'

import { STATE1, SEARCH_HASH } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<GeneBreakdown store={store} searchHash={SEARCH_HASH} />)
})
