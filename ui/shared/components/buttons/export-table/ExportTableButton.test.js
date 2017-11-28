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
    urls: [
      { name: 'Table1', url: '/api/project/table2' },
      { name: 'Table2', url: '/api/project/export_table2' },
    ],
  }

  shallow(<ExportTableButton {...props} />)
})
