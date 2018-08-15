import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'
import { UpdateAnalysisGroup, DeleteAnalysisGroup } from './AnalysisGroupButtons'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

const PROJECT = STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo
const ANALYSIS_GROUP = STATE_WITH_2_FAMILIES.analysisGroupsByGuid.AG0000183_test_group

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  shallow(<UpdateAnalysisGroup project={PROJECT} />)
  shallow(<UpdateAnalysisGroup project={PROJECT} analysisGroup={ANALYSIS_GROUP} />)
  shallow(<DeleteAnalysisGroup project={PROJECT} analysisGroup={ANALYSIS_GROUP} />)
})
