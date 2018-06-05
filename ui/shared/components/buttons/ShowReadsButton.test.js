import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import configureStore from 'redux-mock-store'
import ShowReadsButton from './ShowReadsButton'
import { STATE_WITH_2_FAMILIES } from 'pages/Project/fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)

  shallow(<ShowReadsButton store={store} />)
})
