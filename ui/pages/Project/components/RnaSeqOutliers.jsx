import React from 'react'
import PropTypes from 'prop-types'
import { Header } from 'semantic-ui-react'

import { extent } from 'd3-array'
import { scaleLinear, scaleLog, scalePow } from 'd3-scale'
import { select } from 'd3-selection'

import { GeneSearchLink } from 'shared/components/buttons/SearchResultsLink'
import { initializeD3 } from 'shared/components/graph/d3Utils'

const GRAPH_HEIGHT = 400
const GRAPH_WIDTH = 600
const GRAPH_MARGIN = { top: 10, bottom: 40, right: 30, left: 45 }

class RnaSeqOutliersGraph extends React.PureComponent {

  static propTypes = {
    data: PropTypes.arrayOf(PropTypes.object),
    genesById: PropTypes.object,
  }

  componentDidMount() {
    this.initPlot()
  }

  componentDidUpdate(prevProp) {
    const { data } = this.props
    if (data !== prevProp.data) {
      select(this.container).selectAll('*').remove()
      this.initPlot()
    }
  }

  initPlot = () => {
    const { data: dataArray, genesById } = this.props

    const x = scaleLinear().domain(extent(dataArray.map(d => d.zScore))).range([0, GRAPH_WIDTH])
    const y = scaleLog().domain(extent(dataArray.map(d => d.pValue))).range([0, GRAPH_HEIGHT])
    const r = scalePow().exponent(4).domain(extent(dataArray.map(d => Math.abs(d.deltaPsi)))).range([1, 10])

    const svg = initializeD3(
      select(this.container), { width: GRAPH_WIDTH, height: GRAPH_HEIGHT }, GRAPH_MARGIN, { x, y }, {
        x: { text: 'Z-score', transform: xAxis => xAxis.tickSizeOuter(0) },
        y: { text: '-log(P-value)', transform: yAxis => yAxis.tickSizeOuter(0).ticks(5, val => -Math.log10(val)) },
      },
    )

    // scatterplot
    const dataPoints = svg.append('g').selectAll('dot').data(dataArray).enter()
      .append('g')

    dataPoints.append('circle')
      .attr('cx', d => x(d.zScore))
      .attr('cy', d => y(d.pValue))
      .attr('r', d => (d.deltaPsi === undefined ? 3 : r(Math.abs(d.deltaPsi))))
      .style('fill', 'None')
      .style('stroke', d => (d.isSignificant ? 'red' : 'lightgrey'))

    dataPoints.append('text')
      .text(d => (d.isSignificant ? (genesById[d.geneId] || {}).geneSymbol : null))
      .attr('text-anchor', d => (x(d.zScore) > GRAPH_WIDTH - 100 ? 'end' : 'start'))
      .attr('x', (d) => {
        const xPos = x(d.zScore)
        return xPos + (5 * (xPos > GRAPH_WIDTH - 100 ? -1 : 1))
      })
      .attr('y', d => y(d.pValue))
      .style('fill', 'red')
      .style('font-weight', 'bold')
  }

  setContainerElement = (element) => {
    this.container = element
  }

  render() {
    return (
      <div ref={this.setContainerElement} />
    )
  }

}

const RnaSeqOutliers = React.memo(({ rnaSeqData, genesById, familyGuid, getLocation, searchType, title }) => (
  <div>
    <Header content={title} textAlign="center" />
    <GeneSearchLink
      buttonText={`Search for variants in outlier ${searchType}`}
      icon="search"
      location={rnaSeqData.filter(({ isSignificant }) => isSignificant).map(getLocation).join(',')}
      familyGuid={familyGuid}
      floated="right"
    />
    <RnaSeqOutliersGraph data={rnaSeqData} genesById={genesById} />
  </div>
))

RnaSeqOutliers.propTypes = {
  familyGuid: PropTypes.string.isRequired,
  rnaSeqData: PropTypes.arrayOf(PropTypes.object).isRequired,
  genesById: PropTypes.object,
  getLocation: PropTypes.func,
  searchType: PropTypes.string,
  title: PropTypes.string,
}

export default RnaSeqOutliers
