import React from 'react'
import { shallow } from 'enzyme'
import VerticalArrowToggle from './VerticalArrowToggle'


test('shallow-render without crashing', () => {
  /*
    onClick: React.PropTypes.func.isRequired,
    isPointingDown: React.PropTypes.bool.isRequired,
    color: React.PropTypes.string,
   */

  shallow(<VerticalArrowToggle isPointingDown onClick={() => {}} />)
  shallow(<VerticalArrowToggle onClick={() => {}} />)
})
