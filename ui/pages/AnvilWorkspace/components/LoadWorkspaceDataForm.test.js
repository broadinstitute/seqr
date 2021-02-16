import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import LoadWorkspaceDataForm from './LoadWorkspaceDataForm'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<LoadWorkspaceDataForm namespace="test_namespace" name="test_name" />)
})
