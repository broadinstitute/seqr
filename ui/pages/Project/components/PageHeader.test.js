import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import configureStore from 'redux-mock-store'

import PageHeader from './PageHeader'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    project: PropTypes.object.isRequired,
   */

  const props = {
    match: { params: { breadcrumb: 'a_page' } },
  }
  const store = configureStore()(STATE_WITH_2_FAMILIES)

  shallow(<PageHeader store={store} {...props} />)
})
