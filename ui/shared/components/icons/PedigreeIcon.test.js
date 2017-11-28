import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import PedigreeIcon from './PedigreeIcon'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    sex: PropTypes.string.isRequired,
    affected: PropTypes.string.isRequired,
   */

  const m = shallow(<PedigreeIcon sex="M" affected="A" />)
  expect(m.props().name).toEqual('square')

  const f = shallow(<PedigreeIcon sex="F" affected="A" />)
  expect(f.props().name).toEqual('circle')

  // https://github.com/airbnb/enzyme/tree/master/docs/api/ShallowWrapper
})
