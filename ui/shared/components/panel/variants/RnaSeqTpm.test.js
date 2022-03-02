import React from 'react'
import { connect } from 'react-redux'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'

import { getRnaSeqDataByFamilyGene } from 'redux/selectors'
import RnaSeqTpm from './RnaSeqTpm'
import { STATE1 } from '../fixtures'

configure({ adapter: new Adapter() })

const mapStateToProps = (state, ownProps) => ({
  tpms: getRnaSeqDataByFamilyGene(state)[ownProps.familyGuid].tpms[ownProps.geneId],
})

const ConnectedRnaSeqTpm = connect(mapStateToProps)(RnaSeqTpm)

test('shallow-render without crashing', () => {
  const store = configureStore()(STATE1)

  shallow(<ConnectedRnaSeqTpm store={store} familyGuid="F011652_1" geneId="ENSG00000228198" />)
})
