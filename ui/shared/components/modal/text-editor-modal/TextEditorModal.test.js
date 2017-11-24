import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { TextEditorModalComponent } from './TextEditorModal'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
   modalId: PropTypes.string,
   textEditorModals: PropTypes.object.isRequired,
   onSaveSuccess: PropTypes.func,
   initTextEditorModal: PropTypes.func.isRequired,
   hideTextEditorModal: PropTypes.func.isRequired,
   */

  const props = {
    modalId: 'id',
    textEditorModals: {},
    onSaveSuccess: () => {},
    initTextEditorModal: () => {},
    hideTextEditorModal: () => {},
  }

  shallow(<TextEditorModalComponent {...props} />)
})
