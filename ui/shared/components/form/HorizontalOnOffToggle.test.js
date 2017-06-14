import React from 'react'
import { shallow } from 'enzyme'
import HorizontalOnOffToggle from './HorizontalOnOffToggle'


test('shallow-render without crashing', () => {
  /*
    onClick: PropTypes.func.isRequired,
    isOn: PropTypes.bool.isRequired,
    color: PropTypes.string,
   */

  shallow(<HorizontalOnOffToggle isOn onClick={() => {}} />)
  shallow(<HorizontalOnOffToggle onClick={() => {}} />)
})
