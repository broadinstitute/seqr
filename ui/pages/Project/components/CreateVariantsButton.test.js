import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import configureStore from 'redux-mock-store'
import CreateVariantButton from './CreateVariantButton'
import { STATE_WITH_2_FAMILIES } from 'pages/Project/fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)

  shallow(<CreateVariantButton store={store} family={STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1} />)
})
