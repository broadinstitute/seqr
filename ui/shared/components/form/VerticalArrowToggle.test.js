import React from 'react'
import { shallow } from 'enzyme'
import VerticalArrowToggle from './VerticalArrowToggle'


test('shallow-render without crashing', () => {
  /*
    onClick: PropTypes.func.isRequired,
    isPointingDown: PropTypes.bool.isRequired,
    color: PropTypes.string,
   */

  shallow(<VerticalArrowToggle isPointingDown onClick={() => {}} />)
  shallow(<VerticalArrowToggle onClick={() => {}} />)
})
