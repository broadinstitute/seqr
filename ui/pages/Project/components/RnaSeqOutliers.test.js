import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'

import RnaSeqOutliers from './RnaSeqOutliers'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const { outliers } = STATE_WITH_2_FAMILIES.rnaSeqDataByIndividual.I021476_na19678_1
const RNA_SEQ_DATA = outliers.ENSG00000228198.map(outlier => ({ ...outlier, geneId: 'ENSG00000228198' }))

// The scatterplot itself is drawn with d3 on mount; the project's jest config stubs any module
// whose name contains "d3" (see package.json moduleNameMapper), so deep-mounting it isn't possible.
// Shallow-render instead and assert on the props/content this component controls directly.
test('renders a title, search link, and passes outlier data through to the graph', () => {
  const wrapper = shallow(
    <RnaSeqOutliers
      familyGuid="F011652_1"
      rnaSeqData={RNA_SEQ_DATA}
      genesById={STATE_WITH_2_FAMILIES.genesById}
      getLocation={({ geneId }) => geneId}
      searchType="genes"
      title="Expression Outliers"
      xField="pValue"
    />
  )

  expect(wrapper.find('Header').prop('content')).toEqual('Expression Outliers')
  expect(wrapper.find('GeneSearchLink').prop('location')).toEqual('ENSG00000228198')
  expect(wrapper.find('GeneSearchLink').prop('familyGuid')).toEqual('F011652_1')
  expect(wrapper.find('GeneSearchLink').prop('buttonText')).toEqual('Search for variants in outlier genes')
  expect(wrapper.find('RnaSeqOutliersGraph').prop('data')).toEqual(RNA_SEQ_DATA)
  expect(wrapper.find('RnaSeqOutliersGraph').prop('xField')).toEqual('pValue')
})

test('only includes significant outliers in the search link location', () => {
  const insignificantData = [{ geneId: 'ENSG00000164458', isSignificant: false, pValue: 0.73 }]
  const wrapper = shallow(
    <RnaSeqOutliers
      familyGuid="F011652_1"
      rnaSeqData={[...RNA_SEQ_DATA, ...insignificantData]}
      getLocation={({ geneId }) => geneId}
      searchType="genes"
      title="Expression Outliers"
      xField="pValue"
    />
  )

  expect(wrapper.find('GeneSearchLink').prop('location')).toEqual('ENSG00000228198')
})
