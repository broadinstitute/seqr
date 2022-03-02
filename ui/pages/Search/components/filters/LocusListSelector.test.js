import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'

import LocusListSelector from './LocusListSelector'

import { STATE, LOCUS_LIST } from '../../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE)

  shallow(<LocusListSelector store={store} value={LOCUS_LIST} />)
})
