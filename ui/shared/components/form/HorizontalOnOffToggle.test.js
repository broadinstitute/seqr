import React from 'react'
import { shallow } from 'enzyme'
import HorizontalOnOffToggle from './HorizontalOnOffToggle'


test('shallow-render without crashing', () => {
  /*
    onClick: React.PropTypes.func.isRequired,
    isOn: React.PropTypes.bool.isRequired,
    color: React.PropTypes.string,
   */

  shallow(<HorizontalOnOffToggle isOn onClick={() => {}} />)
  shallow(<HorizontalOnOffToggle onClick={() => {}} />)
})
