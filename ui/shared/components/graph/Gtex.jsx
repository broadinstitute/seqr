import React from 'react'
import { deviation, extent, max, mean,  min, quantile } from 'd3-array'
import { randomNormal } from 'd3-random'
import { scaleBand, scaleLinear } from 'd3-scale'
import { area } from 'd3-shape'

import { compareObjects } from 'shared/utils/sortUtils'
import { initializeD3, Tooltip } from './d3Utils'
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

  const scale = {
    x: scaleBand()
      .rangeRound([0, DIMENSIONS.width])
      .domain(xDomain)
      .paddingInner(0.2),
    y: scaleBand()
      .rangeRound([DIMENSIONS.height, 0])
      .domain(yDomain),
    z: scaleLinear(), // the violin width, domain and range are determined later individually for each violin
  }

  const svg = initializeD3(containerElement, DIMENSIONS, MARGINS, scale, {})

  const tooltip = new Tooltip(containerElement)
  //  TODO fix actually render heatmap
  isoformData.forEach(({ x, y, value }) => {
    svg.append('rect')
      // .attr("row", (d) => `x${this.xList.indexOf(d.x)}`)
      // .attr("col", (d) => `y${this.yList.indexOf(d.y)}`)
      .attr('x', scale.x(x))
      .attr('y', scale.y(y))
      .attr('rx', 5)
      .attr('ry', 5)
      // .attr('class', 'exp-map-cell')
      .attr('width', scale.x.bandwidth())
      .attr('height', scale.y.bandwidth())
      .style('fill', '#eeeeee')
      .on('mouseover', () => {
        tooltip.show(
          `Tissue: ${x}<br/> Isoform: ${y}<br/> TPM: ${value}`,
          x,
          y,
        )
      })
      .on('mouseout', () => {
        tooltip.hide()
      })
      // .style('fill', (d) => {
      //     return useNullColor&&d.value==0?nullColor:this.useLog?this.colorScale(this._log(d.value)):this.colorScale(d.value)
      // })
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
