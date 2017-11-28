import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'

import { HorizontalSpacer, VerticalSpacer } from './Spacers'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    width: PropTypes.number,    height: PropTypes.number,
   */

  shallow(<HorizontalSpacer width={30} />)
  shallow(<VerticalSpacer height={30} />)
})
