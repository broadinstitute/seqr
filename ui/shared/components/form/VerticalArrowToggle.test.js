import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import VerticalArrowToggle from './VerticalArrowToggle'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    onClick: PropTypes.func.isRequired,
    isPointingDown: PropTypes.bool.isRequired,
    color: PropTypes.string,
   */

  shallow(<VerticalArrowToggle isPointingDown onClick={() => {}} />)
  shallow(<VerticalArrowToggle onClick={() => {}} />)
})
