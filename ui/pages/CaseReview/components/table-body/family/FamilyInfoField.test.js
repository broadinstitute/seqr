import React from 'react'
import { shallow } from 'enzyme'
import { FamilyInfoFieldComponent } from './FamilyInfoField'


test('shallow-render without crashing', () => {
  /*
    isPrivate: React.PropTypes.bool,
    isEditable: React.PropTypes.bool,
    fieldName: React.PropTypes.string.isRequired,
    initialText: React.PropTypes.string.isRequired,
    editFamilyInfoModalTitle: React.PropTypes.string,
    editFamilyInfoModalSubmitUrl: React.PropTypes.string,
    showEditFamilyInfoModal: React.PropTypes.func,
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
