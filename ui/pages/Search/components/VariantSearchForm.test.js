import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'

import VariantSearchForm from './VariantSearchForm'

import { STATE, SEARCH_HASH } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE)

  shallow(<VariantSearchForm store={store} match={{ params: { searchHash: SEARCH_HASH } }} />)
})
