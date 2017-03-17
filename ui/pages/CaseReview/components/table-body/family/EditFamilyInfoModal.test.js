import React from 'react'
import { shallow } from 'enzyme'
import { EditFamilyInfoModalComponent } from './EditFamilyInfoModal'
import {
  getEditFamilyInfoModalIsVisible,
  getEditFamilyInfoModalTitle,
  getEditFamilyInfoModaInitialText,
  getEditFamilyInfoModalSubmitUrl,
} from '../../../reducers/rootReducer'

import { STATE1 } from '../../../fixtures'


test('shallow-render without crashing', () => {
  /*
    isVisible: React.PropTypes.bool.isRequired,
    title: React.PropTypes.string,
    initialText: React.PropTypes.string,
    formSubmitUrl: React.PropTypes.string,
    hideEditFamilyInfoModal: React.PropTypes.func.isRequired,
    updateFamiliesByGuid: React.PropTypes.func.isRequired,
   */

  const props = {
    isVisible: getEditFamilyInfoModalIsVisible(STATE1),
    title: getEditFamilyInfoModalTitle(STATE1),
    initialText: getEditFamilyInfoModaInitialText(STATE1),
    formSubmitUrl: getEditFamilyInfoModalSubmitUrl(STATE1),
    hideEditFamilyInfoModal: () => {},
    updateFamiliesByGuid: () => {},
  }

  shallow(<EditFamilyInfoModalComponent {...props} />)
})
