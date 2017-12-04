import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import HorizontalOnOffToggle from './HorizontalOnOffToggle'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    onClick: PropTypes.func.isRequired,
    isOn: PropTypes.bool.isRequired,
    color: PropTypes.string,
   */

  shallow(<HorizontalOnOffToggle isOn onClick={() => {}} />)
  shallow(<HorizontalOnOffToggle onClick={() => {}} />)
})
