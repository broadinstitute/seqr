import React from 'react'
import { shallow } from 'enzyme'

import { HorizontalSpacer, VerticalSpacer } from './Spacers'

test('shallow-render without crashing', () => {
  /*
    width: PropTypes.number,    height: PropTypes.number,
   */

  shallow(<HorizontalSpacer width={30} />)
  shallow(<VerticalSpacer height={30} />)
})
