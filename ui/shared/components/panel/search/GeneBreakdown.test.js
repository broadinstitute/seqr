import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import configureStore from 'redux-mock-store'

import GeneBreakdown from './GeneBreakdown'

import { STATE, SEARCH_HASH } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE)

  shallow(<GeneBreakdown store={store} searchHash={SEARCH_HASH} />)
})
