import React from 'react'
import { render, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'

import { FlexLabel } from './StyledComponents'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const label = render(<FlexLabel hint="AD" label="A long panelapp name" />)

  expect(label.text()).toEqual('A long panelapp nameAD')
})
