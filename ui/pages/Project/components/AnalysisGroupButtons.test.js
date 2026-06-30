import React from 'react'
import { shallow, configure } from 'enzyme'
import configureStore from 'redux-mock-store'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import { UpdateAnalysisGroupButton, DeleteAnalysisGroupButton } from './AnalysisGroupButtons'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

const ANALYSIS_GROUP = STATE_WITH_2_FAMILIES.analysisGroupsByGuid.AG0000183_test_group

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  shallow(<UpdateAnalysisGroupButton store={store} />)
  shallow(<UpdateAnalysisGroupButton store={store} analysisGroup={ANALYSIS_GROUP} />)
  shallow(<DeleteAnalysisGroupButton store={store} analysisGroup={ANALYSIS_GROUP} />)
})
