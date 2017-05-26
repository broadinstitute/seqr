import React from 'react'
import { shallow } from 'enzyme'
import { IndividualInfoEditModalComponent } from './IndividualInfoEditModal'


test('shallow-render without crashing', () => {

  shallow(<IndividualInfoEditModalComponent onSaveSuccess={() => {}} />)
})
