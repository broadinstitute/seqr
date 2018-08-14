import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { LocusListTableComponent } from './LocusListTable'

import { LOCUS_LIST } from '../panel/fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<LocusListTableComponent locusListsByGuid={{[LOCUS_LIST.locusListGuid]: LOCUS_LIST}} />)
})
