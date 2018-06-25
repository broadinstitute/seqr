import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import PedigreeIcon from './PedigreeIcon'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*w
    sex: PropTypes.string.isRequired,
    affected: PropTypes.string.isRequired,
   */

  const m = shallow(<PedigreeIcon sex="M" affected="A" />)
  expect(m.props().content.props.children).toEqual(expect.arrayContaining(['Male', 'Affected']))

  const f = shallow(<PedigreeIcon sex="F" affected="U" />)
  expect(f.props().content.props.children).toEqual(expect.arrayContaining(['Female', 'Unknown']))

  // https://github.com/airbnb/enzyme/tree/master/docs/api/ShallowWrapper
})
