import React from 'react'
import { shallow } from 'enzyme'
import RichTextEditorModal from './RichTextEditorModal'


test('shallow-render without crashing', () => {
  /*
    title: React.PropTypes.string.isRequired,
    formSubmitUrl: React.PropTypes.string.isRequired,
    onSave: React.PropTypes.func,
    onClose: React.PropTypes.func.isRequired,
    initialText: React.PropTypes.string,
   */

  const props = {
    title: 'modal title',
    formSubmitUrl: 'http://url/',
    initialText: 'text',
    onSave: () => {},
    onClose: () => {},
  }

  shallow(<RichTextEditorModal {...props} />)
})
