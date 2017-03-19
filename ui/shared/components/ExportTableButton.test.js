import React from 'react'
import { shallow } from 'enzyme'
import ExportTableButton from './ExportTableButton'


test('shallow-render without crashing', () => {
  /*
    urls: React.PropTypes.array.isRequired,
   */
  const props = {
    urls: [
      { name: 'Table1', url: '/api/project/table2' },
      { name: 'Table2', url: '/api/project/export_table2' },
    ],
  }

  shallow(<ExportTableButton {...props} />)
})
