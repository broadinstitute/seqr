import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import LocusListTables from './LocusListTables'
import configureStore from "redux-mock-store";
import { STATE1 } from '../panel/fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<LocusListTables store={store} />)
})
