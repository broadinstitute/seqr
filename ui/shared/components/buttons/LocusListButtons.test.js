import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { CreateLocusList, UpdateLocusList, DeleteLocusList } from './LocusListButtons'

import { LOCUS_LIST } from '../panel/fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<CreateLocusList />)
  shallow(<UpdateLocusList locusList={LOCUS_LIST} />)
  shallow(<DeleteLocusList locusList={LOCUS_LIST} />)
})
