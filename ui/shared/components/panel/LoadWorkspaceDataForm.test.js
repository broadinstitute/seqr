import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import LoadWorkspaceDataForm from './LoadWorkspaceDataForm'
import { STATE1 } from './fixtures'

configure({ adapter: new Adapter() })

const params = { namespace: 'test_namespace', name: 'test_name' }

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)
  shallow(<LoadWorkspaceDataForm store={store} params={params} />)
})
