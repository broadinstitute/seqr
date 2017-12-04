import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import SaveStatus from './SaveStatus'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    status: PropTypes.number,
    errorMessage: PropTypes.string,
   */

  shallow(<SaveStatus status={SaveStatus.NONE} />)
  shallow(<SaveStatus status={SaveStatus.IN_PROGRESS} />)
  shallow(<SaveStatus status={SaveStatus.SUCCEEDED} />)
  shallow(<SaveStatus status={SaveStatus.ERROR} errorMessage="some error" />)
})
