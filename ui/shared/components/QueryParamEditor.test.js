import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'

import { QueryParamEditorComponent } from './QueryParamEditor'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {

  const ValDisplay = ({ currentQueryParam }) => <div>{currentQueryParam}</div>

  const queryParamEditor = mount(
    <QueryParamEditorComponent queryParam="q" history={[]} location={{ search: '?q=paramValue' }}>
      <ValDisplay />
    </QueryParamEditorComponent>)
  expect(queryParamEditor.text()).toEqual('paramValue')
})
