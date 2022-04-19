import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { getProject } from '../selectors'
import CaseReviewTable from './CaseReview'

import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    project: PropTypes.object.isRequired,
   */

  const store = configureStore()(STATE_WITH_2_FAMILIES)
  shallow(<CaseReviewTable store={store} />)
})
