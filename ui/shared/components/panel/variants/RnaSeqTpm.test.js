import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'

import { getRnaSeqDataByFamilyGene } from 'redux/selectors'
import RnaSeqTpm from './RnaSeqTpm'
import { STATE1 } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<RnaSeqTpm store={store} familyGuid="F011652_1" geneId="ENSG00000228198" />)
})
