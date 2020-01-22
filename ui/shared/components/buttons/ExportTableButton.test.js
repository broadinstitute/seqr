import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import ExportTableButton from './ExportTableButton'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    urls: PropTypes.array.isRequired,
   */
  const props = {
    downloads: [
      { name: 'Table1', url: '/api/project/table2' },
      { name: 'Table2', data: { rawData: [ { a: 1 }, { a: 2 }], processRow: row => [row.a] } },
    ],
  }

  shallow(<ExportTableButton {...props} />)
})
