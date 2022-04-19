import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import TagFieldView from './TagFieldView'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const props = {
    isEditable: true,
    field: 'SOME_NAME',
    initialValues: { SOME_NAME: [{ name: 'a' }, { name: 'b' }] },
    tagOptions: [{ name: 'a' }, { name: 'b' }, { name: 'c' }],
    onSubmit: () => {},
  }

  shallow(<TagFieldView {...props} />)
})
