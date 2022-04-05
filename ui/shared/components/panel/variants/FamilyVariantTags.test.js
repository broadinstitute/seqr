import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import FamilyVariantTags from './FamilyVariantTags'

import { STATE1, VARIANT, SV_VARIANT } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<FamilyVariantTags store={store} variant={VARIANT} familyGuid={VARIANT.familyGuids[0]} />)
  shallow(<FamilyVariantTags store={store} variant={SV_VARIANT} familyGuid={SV_VARIANT.familyGuids[0]} />)
})
