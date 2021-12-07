import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { extent } from 'd3-array'
import { axisBottom, axisLeft } from 'd3-axis'
import { scaleLinear, scaleLog } from 'd3-scale'
import { select } from 'd3-selection'

import DataLoader from 'shared/components/DataLoader'
import { loadRnaSeqData } from '../reducers'
import { getRnaSeqDataByIndividual, getRnaSeqDataLoading } from '../selectors'

const GRAPH_HEIGHT = 400
const GRAPH_WIDTH = 600
const GRAPH_MARGIN = { top: 10, bottom: 30, right: 30, left: 50 }

class RnaSeqOutliersGraph extends React.PureComponent {

  static propTypes = {
    data: PropTypes.object,
  }

  componentDidMount() {
    const { data } = this.props
    const dataArray = Object.values(data)
    console.log(dataArray.filter(({ showDetail }) => showDetail))

    const svg = select(this.svg).append('g')
      .attr('transform', `translate(${GRAPH_MARGIN.left},${GRAPH_MARGIN.top})`)

    const x = scaleLinear().domain(extent(dataArray.map(d => d.zScore))).range([0, GRAPH_WIDTH])
    const y = scaleLog().domain(extent(dataArray.map(d => d.pValue))).range([0, GRAPH_HEIGHT])

    svg.append('g')
      .attr('transform', `translate(0,${GRAPH_HEIGHT + 5})`)
      .call(axisBottom(x).tickSizeOuter(0))

    svg.append('g')
      .attr('transform', 'translate(-10,0)')
      .call(axisLeft(y).tickSizeOuter(0))

    svg.append('g').selectAll('dot').data(dataArray).enter()
      .append('circle')
      .attr('cx', d => x(d.zScore))
      .attr('cy', d => y(d.pValue))
      .attr('r', 3)
      .style('fill', d => (d.showDetail ? 'red' : 'lightgrey'))
  }

  setSvgElement = (element) => {
    this.svg = element
  }

  render() {
    return (
      <svg
        ref={this.setSvgElement}
        width={GRAPH_WIDTH + GRAPH_MARGIN.left + GRAPH_MARGIN.right}
        height={GRAPH_HEIGHT + GRAPH_MARGIN.top + GRAPH_MARGIN.bottom}
      />
    )
  }

}

const BaseRnaSeqOutliers = React.memo(({ sample, rnaSeqData, loading, load }) => (
  <DataLoader content={rnaSeqData} contentId={sample.individualGuid} load={load} loading={loading}>
    <RnaSeqOutliersGraph data={rnaSeqData} />
  </DataLoader>
))

BaseRnaSeqOutliers.propTypes = {
  sample: PropTypes.object,
  rnaSeqData: PropTypes.object,
  loading: PropTypes.bool,
  load: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  rnaSeqData: getRnaSeqDataByIndividual(state)[ownProps.sample.individualGuid],
  loading: getRnaSeqDataLoading(state),
})

const mapDispatchToProps = {
  load: loadRnaSeqData,
}

export default connect(mapStateToProps, mapDispatchToProps)(BaseRnaSeqOutliers)
