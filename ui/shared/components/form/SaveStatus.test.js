import React from 'react'
import { shallow } from 'enzyme'
import SaveStatus from './SaveStatus'


test('shallow-render without crashing', () => {
  /*
    status: React.PropTypes.number,
    errorMessage: React.PropTypes.string,
   */

  shallow(<SaveStatus status={SaveStatus.NONE} />)
  shallow(<SaveStatus status={SaveStatus.IN_PROGRESS} />)
  shallow(<SaveStatus status={SaveStatus.SUCCEEDED} />)
  shallow(<SaveStatus status={SaveStatus.ERROR} errorMessage="some error" />)
})
