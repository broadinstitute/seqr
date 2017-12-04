import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { RichTextEditorModalComponent } from './RichTextEditorModal'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
   modalId: PropTypes.string,
   richTextEditorModals: PropTypes.object.isRequired,
   onSaveSuccess: PropTypes.func,
   initRichTextEditorModal: PropTypes.func.isRequired,
   hideRichTextEditorModal: PropTypes.func.isRequired,
   */

  const props = {
    modalId: 'id',
    richTextEditorModals: {},
    onSaveSuccess: () => {},
    initModal: () => {},
    hideModal: () => {},
  }

  shallow(<RichTextEditorModalComponent {...props} />)
})
