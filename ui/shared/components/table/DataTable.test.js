import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import DataTable from './DataTable'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<DataTable
    data={[{ id: 1, a: 'apple', b: 'banana', c: 'cat' }, { id: 2 }]}
    columns={[{ name: 'a' }, { name: 'b' }, { name: 'c' }]}
    idField="id"
    defaultSortColumn="a"
  />)
})
