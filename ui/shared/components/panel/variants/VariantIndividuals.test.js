import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { getUser } from 'redux/selectors'
import VariantIndividuals from './VariantIndividuals'
import { STATE1, VARIANT } from '../fixtures'
import configureStore from "redux-mock-store";

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<VariantIndividuals store={store} variant={VARIANT} />)
})
