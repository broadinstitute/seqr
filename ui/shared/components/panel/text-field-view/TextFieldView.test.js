import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import TextFieldView from './TextFieldView'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
   isRichText: PropTypes.bool,
   isPrivate: PropTypes.bool,
   isEditable: PropTypes.bool,
   textEditorId: PropTypes.string,
   textEditorSubmitUrl: PropTypes.string,
   textEditorTitle: PropTypes.string,
   fieldName: PropTypes.string.isRequired,
   initialText: PropTypes.string,
   */

  const props = {
    isRichText: true,
    isPrivate: true,
    isEditable: false,
    textEditorId: 'test title',
    textEditorSubmitUrl: 'http://test',
    textEditorTitle: 'test title',
    fieldName: 'SOME_NAME',
    initialText: 'SOME INITIAL TEXT WITH UNIØDE´',
    showTextEditorModal: () => {},
  }

  shallow(<TextFieldView {...props} />)

  const props2 = {
    isRichText: false,
    isPrivate: false,
    isEditable: false,
    textEditorId: 'test title',
    textEditorSubmitUrl: 'http://test',
    textEditorTitle: 'test title',
    fieldName: 'SOME_NAME',
    initialText: 'SOME INITIAL TEXT WITH UNIØDE´',
    showTextEditorModal: () => {},
  }

  shallow(<TextFieldView {...props2} />)
})
