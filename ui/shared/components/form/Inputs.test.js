import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { SearchInput } from './Inputs'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {

  shallow(<SearchInput options={[ { title: 'Opt 1', title: 'Opt 2' }]} value="Opt 3" />)
})
