import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import configureStore from 'redux-mock-store'
import ShowPhenotipsModalButton from './ShowPhenotipsModalButton'

import { STATE1 } from '../panel/fixtures'
import {STATE_WITH_2_FAMILIES} from "../../../pages/Project/fixtures";

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
   project: PropTypes.object.isRequired,
   individual: PropTypes.object.isRequired,
   showPhenotipsModal: PropTypes.func.isRequired,
   */

  const props = {
    individual: STATE1.individualsByGuid.I021474_na19679,
    isViewOnly: false,
  }
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  shallow(<ShowPhenotipsModalButton store={store} {...props} />)
})
