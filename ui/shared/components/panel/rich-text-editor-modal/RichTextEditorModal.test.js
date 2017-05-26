import React from 'react'
import { shallow } from 'enzyme'
import { RichTextEditorModalComponent } from './RichTextEditorModal'


test('shallow-render without crashing', () => {
  /*
    title: PropTypes.string.isRequired,
    formSubmitUrl: PropTypes.string.isRequired,
    initialText: PropTypes.string,
    onSaveSuccess: PropTypes.func,
   */

  const props = {
    title: 'modal title',
    formSubmitUrl: 'http://url/',
    initialText: 'text',
    onSaveSuccess: () => {},
  }

  shallow(<RichTextEditorModalComponent {...props} />)
})
