import React from 'react'
import { shallow } from 'enzyme'
import { TextFieldViewComponent } from './TextFieldView'


test('shallow-render without crashing', () => {
  /*
    isPrivate: PropTypes.bool,
    isEditable: PropTypes.bool,
    fieldName: PropTypes.string.isRequired,
    initialText: PropTypes.string.isRequired,
    richTextEditorModalTitle: PropTypes.string,
    richTextEditorModalSubmitUrl: PropTypes.string,
    showrichTextEditorModal: PropTypes.func,
   */

  const props = {
    isPrivate: true,
    isEditable: false,
    fieldName: 'SOME_NAME',
    initialText: 'SOME INITIAL TEXT WITH UNIØDE´',
    textEditorModalTitle: 'test title',
    textEditorModalSubmitUrl: 'http://test',
    showTextEditorModal: () => {},
  }

  shallow(<TextFieldViewComponent {...props} />)
})
