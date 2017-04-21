import React from 'react'
import { shallow } from 'enzyme'
import RichTextEditor from './RichTextEditor'


test('shallow-render without crashing', () => {
  /*
    id: React.PropTypes.string.isRequired,
    initialText: React.PropTypes.string,
   */

  const props = {
    id: 'someid',
    initialText: 'some text',
  }

  shallow(<RichTextEditor {...props} />)
})
