import React from 'react'
import { shallow } from 'enzyme'
import { FamilyInfoFieldComponent } from './FamilyInfoField'


test('shallow-render without crashing', () => {
  /*
    isPrivate: PropTypes.bool,
    isEditable: PropTypes.bool,
    fieldName: PropTypes.string.isRequired,
    initialText: PropTypes.string.isRequired,
    editFamilyInfoModalTitle: PropTypes.string,
    editFamilyInfoModalSubmitUrl: PropTypes.string,
    showEditFamilyInfoModal: PropTypes.func,
   */

  const props = {
    isPrivate: true,
    isEditable: false,
    fieldName: 'SOME_NAME',
    initialText: 'SOME INITIAL TEXT WITH UNIØDE´',
    editFamilyInfoModalTitle: 'test title',
    editFamilyInfoModalSubmitUrl: 'http://test',
    showEditFamilyInfoModal: () => {},
  }

  shallow(<FamilyInfoFieldComponent {...props} />)
})
