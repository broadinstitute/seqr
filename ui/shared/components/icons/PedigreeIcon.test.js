import React from 'react'
import { shallow } from 'enzyme'
import PedigreeIcon from './PedigreeIcon'


test('shallow-render without crashing', () => {
  /*
    sex: PropTypes.string.isRequired,
    affected: PropTypes.string.isRequired,
   */

  const m = shallow(<PedigreeIcon sex="M" affected="A" />)
  expect(m.props().name).toEqual('square')

  const f = shallow(<PedigreeIcon sex="F" affected="A" />)
  expect(f.props().name).toEqual('circle')

  const u = shallow(<PedigreeIcon sex="U" affected="A" />)
  expect(u.props().name).toEqual('help')

  const x = shallow(<PedigreeIcon sex="X" affected="A" />)
  expect(x.props().name).toEqual('warning sign')

  // https://github.com/airbnb/enzyme/tree/master/docs/api/ShallowWrapper
})
