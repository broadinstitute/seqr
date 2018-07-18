import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { LocusListDetail } from './LocusListDetail'

import { LOCUS_LIST } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<LocusListDetail locusList={LOCUS_LIST}  />)
})
