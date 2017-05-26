import React from 'react'
import { shallow } from 'enzyme'
import { FamilyInfoEditModalComponent } from './FamilyInfoEditModal'


test('shallow-render without crashing', () => {

  shallow(<FamilyInfoEditModalComponent onSaveSuccess={() => {}} />)
})
