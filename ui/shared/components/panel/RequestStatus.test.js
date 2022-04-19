import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import RequestStatus from './RequestStatus'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    status: PropTypes.number,
    errorMessage: PropTypes.string,
   */

  shallow(<RequestStatus status={RequestStatus.NONE} />)
  shallow(<RequestStatus status={RequestStatus.IN_PROGRESS} />)
  shallow(<RequestStatus status={RequestStatus.SUCCEEDED} />)
  shallow(<RequestStatus status={RequestStatus.ERROR} errorMessage="some error" />)
})
