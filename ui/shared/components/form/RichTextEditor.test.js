import React from 'react'
import { shallow } from 'enzyme'
import RichTextEditor from './RichTextEditor'


test('shallow-render without crashing', () => {
  /*
    id: PropTypes.string.isRequired,
    initialText: PropTypes.string,
   */

  const props = {
    id: 'someid',
    initialText: 'some text',
  }

  shallow(<RichTextEditor {...props} />)
})
