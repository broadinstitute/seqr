import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import configureStore from 'redux-mock-store'
import LocusListDetail from './LocusListDetail'

import { STATE1, LOCUS_LIST_GUID } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
   const store = configureStore()(STATE1)

  shallow(<LocusListDetail store={store} locusListGuid={LOCUS_LIST_GUID}  />)
})
