import React from 'react'
import { shallow } from 'enzyme'

import { HorizontalSpacer, VerticalSpacer } from './Spacers'

test('shallow-render without crashing', () => {
  /*
    width: React.PropTypes.number,    height: React.PropTypes.number,
   */

  shallow(<HorizontalSpacer width={30} />)
  shallow(<VerticalSpacer height={30} />)
})
