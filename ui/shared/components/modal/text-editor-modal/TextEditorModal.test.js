import React from 'react'
import { shallow } from 'enzyme'
import { TextEditorModalComponent } from './TextEditorModal'


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
