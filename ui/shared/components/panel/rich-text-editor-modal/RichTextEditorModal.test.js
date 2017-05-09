import React from 'react'
import { shallow } from 'enzyme'
import { RichTextEditorModalComponent } from './RichTextEditorModal'


test('shallow-render without crashing', () => {
  /*
    title: PropTypes.string.isRequired,
    formSubmitUrl: PropTypes.string.isRequired,
    onSave: PropTypes.func,
    onClose: PropTypes.func.isRequired,
    initialText: PropTypes.string,
   */

  const props = {
    title: 'modal title',
    formSubmitUrl: 'http://url/',
    initialText: 'text',
    onSave: () => {},
    onClose: () => {},
  }

  shallow(<RichTextEditorModalComponent {...props} />)
})
