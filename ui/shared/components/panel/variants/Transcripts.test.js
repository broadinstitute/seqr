import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import configureStore from 'redux-mock-store'
import Transcripts from './Transcripts'

import { STATE1, GENE } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<Transcripts store={store} gene={GENE} />)
})
