import React from 'react'
import { deviation, extent, max, mean,  min, quantile } from 'd3-array'
import { randomNormal } from 'd3-random'
import { scaleBand, scaleLinear, scaleSequential } from 'd3-scale'
import { interpolatePurples } from 'd3-scale-chromatic'
import { area } from 'd3-shape'

import { compareObjects } from 'shared/utils/sortUtils'
import { initializeD3, log, Tooltip } from './d3Utils'
import GtexLauncher, { queryGtex } from './GtexLauncher'

const MARGINS = {
  top: 10,
  right: 50,
  bottom: 150,
  left: 100,
}
const DIMENSIONS = {
  width: window.innerWidth * 0.8,
  height: 400,
}

// Code adapted from https://github.com/broadinstitute/gtex-viz/blob/f9d18299b2bcb69e4a919a4afa359c99a33fbc3b/src/TranscriptBrowser.js
// and https://github.com/broadinstitute/gtex-viz/blob/f9d18299b2bcb69e4a919a4afa359c99a33fbc3b/src/modules/Heatmap.js

const renderIsoformHeatmap = (isoformData, containerElement) => {
  const xDomain = [...new Set(isoformData.map(({ x }) => x))].sort(compareObjects('x'))
  const yDomain = [...new Set(isoformData.map(({ y }) => y))].sort(compareObjects('y'))

  const dimensions = {
    ...DIMENSIONS,
    height: yDomain.length * 15,
  }

  const scale = {
    x: scaleBand()
      .rangeRound([0, dimensions.width])
      .domain(xDomain)
      .paddingInner(0.2),
    y: scaleBand()
      .rangeRound([dimensions.height, 0])
      .domain(yDomain)
      .paddingInner(0.1),
    color: scaleSequential(interpolatePurples)
      .domain([0, max(isoformData.map(({ value }) => log(value)))]),
  }

  const svg = initializeD3(containerElement, dimensions, MARGINS, scale, {})

  const tooltip = new Tooltip(containerElement)
  isoformData.forEach(({ x, y, value }) => {
    svg.append('rect')
      .attr('row', `x${xDomain.indexOf(x)}`)
      .attr('col', `y${yDomain.indexOf(y)}`)
      .attr('x', scale.x(x))
      .attr('y', scale.y(y))
      .attr('rx', 5)
      .attr('ry', 5)
      .attr('width', scale.x.bandwidth())
      .attr('height', scale.y.bandwidth())
      .style('fill', '#eeeeee')
      .on('mouseover', () => {
        tooltip.show(`Tissue: ${x}<br/> Isoform: ${y}<br/> TPM: ${value}`, scale.x(x), scale.y(y))
      })
      .on('mouseout', () => {
        tooltip.hide()
      })
      .style('fill', value === 0 ? '#DDDDDD' : scale.color(log(value)))
  })
}

// seqr-specific code

const loadTissueData = onSuccess => queryGtex('dataset/tissueSiteDetail', {}, onSuccess)

const renderGtex = (expressionData, tissueData, containerElement) => {
  if ((expressionData?.medianTranscriptExpression || []).length < 1) {
    return
  }
  const tissueLookup = tissueData.data.reduce(
    (acc, { tissueSiteDetailId, ...data }) => ({ ...acc, [tissueSiteDetailId]: data }), {},
  )
  //  TODO better property names
  const isoformData = expressionData.medianTranscriptExpression.map(({ median, transcriptId, tissueSiteDetailId, gencodeId }) => ({
    value: Number(median),
    displayValue: Number(median),
    y: transcriptId,
    x: tissueLookup[tissueSiteDetailId]?.tissueSiteDetail,
    tissueId: tissueSiteDetailId,
    id: gencodeId,
  }))
  renderIsoformHeatmap(isoformData, containerElement)
}

export default props => (
  <GtexLauncher renderGtex={renderGtex} fetchAdditionalData={loadTissueData} expressionPath="clusteredMedianTranscriptExpression" {...props} />
)
