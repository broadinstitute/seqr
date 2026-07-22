import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'

// This project's jest config maps every module whose name contains "d3" (see package.json
// moduleNameMapper) - which includes d3-array, d3-scale, d3-selection, and
// shared/components/graph/d3Utils - to config/jest/fakeD3.js, so this is the real FakeD3Selection
// the component below draws with, not a separate mock.
import { FakeD3Selection } from 'd3-selection'
import RnaSeqOutliers, { RnaSeqOutliersGraph } from './RnaSeqOutliers'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

// The fake d3Utils.initializeD3 ignores the axis config it is given (there is nothing
// meaningful for it to draw without a real DOM), so it never invokes the x/y "transform"
// callbacks RnaSeqOutliersGraph builds. This spy wraps the real fake so those callbacks - and
// the tick-label formatter they build - actually run, without needing a real d3 axis/DOM.
jest.mock('shared/components/graph/d3Utils', () => {
  const actual = jest.requireActual('shared/components/graph/d3Utils')
  return {
    ...actual,
    initializeD3: (containerElement, dimensions, margin, scales, axes) => {
      axes.x.transform({ tickSizeOuter: () => ({}) })
      axes.y.transform({ tickSizeOuter: () => ({ ticks: (n, tickFormat) => tickFormat(0.01) }) })
      return actual.initializeD3(containerElement, dimensions, margin, scales, axes)
    },
  }
})

const RNA_SEQ_DATA = STATE_WITH_2_FAMILIES.rnaSeqDataByIndividual.I021476_na19678_1.outliers.ENSG00000228198

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

test('handles a container element ref callback', () => {
  const wrapper = shallow(
    <RnaSeqOutliersGraph data={GRAPH_DATA} genesById={STATE_WITH_2_FAMILIES.genesById} xField="zScore" />,
  )
  const fakeElement = {}
  wrapper.instance().setContainerElement(fakeElement)
  expect(wrapper.instance().container).toBe(fakeElement)
})

test('only includes significant outliers in the search link location', () => {
  const insignificantData = STATE_WITH_2_FAMILIES.rnaSeqDataByIndividual.I021474_na19679_1.outliers.ENSG00000164458
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

// The scale math itself is d3's own responsibility; scaleLinear/scaleLog are stubbed as identity
// functions so these tests can focus on what RnaSeqOutliersGraph itself computes and draws: which
// points get circles/labels, how they're styled, and how they're positioned/anchored.
const GRAPH_DATA = [
  ...STATE_WITH_2_FAMILIES.rnaSeqDataByIndividual.I021476_na19678_1.outliers.ENSG00000228198,
  ...STATE_WITH_2_FAMILIES.rnaSeqDataByIndividual.I021476_na19678_1.outliers.ENSG00000164458,
  ...STATE_WITH_2_FAMILIES.rnaSeqDataByIndividual.I021474_na19679_1.outliers.ENSG00000164458,
]

describe('RnaSeqOutliersGraph', () => {
  beforeEach(() => {
    FakeD3Selection.reset()
  })

  test('plots one circle per datum, styled by significance', () => {
    shallow(
      <RnaSeqOutliersGraph data={GRAPH_DATA} genesById={STATE_WITH_2_FAMILIES.genesById} xField="zScore" />,
    )

    const [circles] = FakeD3Selection.getAppended('circle')
    expect(circles.attrs.cx).toEqual([-5, 20, 550])
    expect(circles.attrs.cy).toEqual([0.0004, 0.0073, 0.73])  // NOPMD
    expect(circles.styles.fill).toEqual(['None', 'None', 'None'])
    expect(circles.styles.stroke).toEqual(['red', 'red', 'lightgrey'])
  })

  test('only labels significant points, with their gene symbol', () => {
    shallow(
      <RnaSeqOutliersGraph data={GRAPH_DATA} genesById={STATE_WITH_2_FAMILIES.genesById} xField="zScore" />,
    )

    const [text] = FakeD3Selection.getAppended('text')
    expect(text.texts).toEqual(['OR2M3', 'TBXT', null])
    expect(text.styles.fill).toEqual(['red', 'red', 'red'])
    expect(text.styles['font-weight']).toEqual(['bold', 'bold', 'bold'])
  })

  test('labels a significant point with an unknown gene as undefined', () => {
    const unknownGeneData = [
      { ...GRAPH_DATA[0], geneId: 'ENSG00000UNKNOWN', isSignificant: true },
    ]
    shallow(
      <RnaSeqOutliersGraph data={unknownGeneData} genesById={STATE_WITH_2_FAMILIES.genesById} xField="zScore" />,
    )

    const [text] = FakeD3Selection.getAppended('text')
    expect(text.texts).toEqual([undefined])
  })

  test('anchors labels to avoid running off the right edge of the graph', () => {
    shallow(
      <RnaSeqOutliersGraph data={GRAPH_DATA} genesById={STATE_WITH_2_FAMILIES.genesById} xField="zScore" />,
    )

    // GRAPH_WIDTH (600) - 100 = 500: points past that flip anchor/offset to keep the label on-graph
    const [text] = FakeD3Selection.getAppended('text')
    expect(text.attrs['text-anchor']).toEqual(['start', 'start', 'end'])
    expect(text.attrs.x).toEqual([0, 25, 545])
  })

  test('re-draws the graph when the data changes', () => {
    const wrapper = shallow(
      <RnaSeqOutliersGraph data={GRAPH_DATA} genesById={STATE_WITH_2_FAMILIES.genesById} xField="zScore" />,
    )
    expect(FakeD3Selection.getAppended('circle')).toHaveLength(1)
    expect(FakeD3Selection.removeCallCount).toEqual(0)

    const newData = [{ geneId: 'ENSG00000164458', zScore: 5, pValue: 0.9, isSignificant: false }]
    wrapper.setProps({ data: newData })

    expect(FakeD3Selection.removeCallCount).toEqual(1)
    const circles = FakeD3Selection.getAppended('circle')
    expect(circles).toHaveLength(2)
    expect(circles[1].attrs.cx).toEqual([5])
  })

  test('does not re-draw when unrelated props change', () => {
    const wrapper = shallow(
      <RnaSeqOutliersGraph data={GRAPH_DATA} genesById={STATE_WITH_2_FAMILIES.genesById} xField="zScore" />,
    )
    expect(FakeD3Selection.getAppended('circle')).toHaveLength(1)

    wrapper.setProps({ xField: 'zScore' })

    expect(FakeD3Selection.removeCallCount).toEqual(0)
    expect(FakeD3Selection.getAppended('circle')).toHaveLength(1)
  })
})
