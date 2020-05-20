import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import NullableBoolFieldView from './NullableBoolFieldView'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const props = {
    isEditable: true,
    initialValues: { field_1: true, field_2: false, field_3: null },
    onSubmit: () => {},
  }

  shallow(<NullableBoolFieldView field="field_1" {...props} />)
  shallow(<NullableBoolFieldView field="field_2" {...props} />)
  shallow(<NullableBoolFieldView field="field_3" {...props} />)

})
