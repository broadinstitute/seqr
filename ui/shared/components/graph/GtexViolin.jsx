import React from 'react'
import { deviation, extent, max, mean, median, min, quantile } from 'd3-array'
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
  left: 50,
}
const DIMENSIONS = {
  width: window.innerWidth * 0.8,
  height: 400,
}

// Code adapted from https://github.com/broadinstitute/gtex-viz/blob/8d65862fbe7e5ab9b4d5be419568754e0d17bb07/src/GeneExpressionViolinPlot.js

const drawViolin = (svg, scale, tooltip) => (entry) => {
  const violinG = svg.append('g')
    .datum(entry)

  const eDomain = extent(entry.values) // get the max and min in entry.values
  const q1 = quantile(entry.values, 0.25)
  const q3 = quantile(entry.values, 0.75)

  // get the vertices
  const rangeDeviation = (q3 - q1) / 1.34
  const kernelBandwidth = 1.06 * Math.min(deviation(entry.values), rangeDeviation) * (entry.values.length ** -0.2)
  // use up to 100 vertices along the Y axis (to create the violin path)
  const vertices = scale.y.ticks(100).map(x => [x, mean(entry.values, (v) => {
    const u = (x - v) / kernelBandwidth
    return (1 / Math.sqrt(2 * Math.PI)) * Math.exp(-0.5 * u * u)
  }) / kernelBandwidth]).filter(
    // filter the vertices that aren't in the entry.values
    d => d[0] >= eDomain[0] && d[0] <= eDomain[1],
  )

  if (vertices.length < 1 || vertices.some(Number.isNaN)) {
    return
  }

  // define the z scale -- the violin width
  const zMax = max(vertices, d => Math.abs(d[1]))
  scale.z
    .domain([-zMax, zMax])
    .range([scale.x(entry.label), scale.x(entry.label) + scale.x.bandwidth()])

  // visual rendering
  const violin = area()
    .x0(d => scale.z(d[1]))
    .x1(d => scale.z(-d[1]))
    .y(d => scale.y(d[0]))

  const vPath = violinG.append('path')
    .datum(vertices)
    .attr('d', violin)
    .style('fill', () => entry.color)
    .style('opacity', 0.6)

  // boxplot
  const z = scale.z.domain()[1] / 3
  const x = scale.z(-z)

  // interquartile range
  violinG.append('rect')
    .attr('x', x)
    .attr('y', scale.y(q3))
    .attr('width', Math.abs(x - scale.z(z)))
    .attr('height', Math.abs(scale.y(q3) - scale.y(q1)))
    .style('fill', '#555f66')

  // the median line
  const medianY = scale.y(entry.median)
  violinG.append('line')
    .attr('x1', x)
    .attr('x2', scale.z(z))
    .attr('y1', medianY)
    .attr('y2', medianY)
    .style('stroke', '#fff')
    .style('stroke-width', '2px')

  const jitter = randomNormal(0, z / 2)
  const iqr = Math.abs(q3 - q1)
  const upper = max(entry.values.filter(d => d <= q3 + (iqr * 1.5)))
  const lower = min(entry.values.filter(d => d >= q1 - (iqr * 1.5)))
  const outliers = entry.values.filter(d => d < lower || d > upper)
  violinG.append('g')
    .selectAll('circle')
    .data(outliers)
    .enter()
    .append('circle')
    .attr('cx', () => scale.z(jitter()))
    .attr('cy', d => scale.y(d))
    .attr('fill', entry.color)
    .attr('r', 1)

  // mouse events
  violinG.on('mouseover', () => {
    vPath.style('opacity', 1)
    tooltip.show(
      `${entry.label}<br/>Sample size: ${entry.values.length}<br/>Median TPM: ${entry.median.toPrecision(4)}<br/>`,
      x + 70,
      medianY < 40 ? 10 : medianY - 40,
    )
  })
  violinG.on('mouseout', () => {
    vPath.style('opacity', 0.6)
  })
}

const renderViolinPlot = (violinPlotData, containerElement) => {
  const xDomain = violinPlotData.map(({ label }) => label)
  const yDomain = extent(violinPlotData.reduce((acc, { values }) => ([...acc, ...values]), []))

  const scale = {
    x: scaleBand()
      .rangeRound([0, DIMENSIONS.width])
      .domain(xDomain)
      .paddingInner(0.2),
    y: scaleLinear()
      .rangeRound([DIMENSIONS.height, 0])
      .domain(yDomain),
    z: scaleLinear(), // the violin width, domain and range are determined later individually for each violin
  }

  const svg = initializeD3(containerElement, DIMENSIONS, MARGINS, scale, {
    y: {
      text: 'TPM',
      transform: yAxis => yAxis.tickValues(scale.y.ticks(5)),
    },
  })

  const tooltip = new Tooltip(containerElement)
  violinPlotData.forEach(drawViolin(svg, scale, tooltip))
}

// seqr-specific code

const loadTissueData = onSuccess => queryGtex('dataset/tissueSiteDetail', {}, onSuccess)

const renderGtex = (expressionData, tissueData, containerElement) => {
  if ((expressionData?.data || []).length < 1) {
    return
  }
  const tissueLookup = tissueData.data.reduce(
    (acc, { tissueSiteDetailId, ...data }) => ({ ...acc, [tissueSiteDetailId]: data }), {},
  )
  const violinPlotData = expressionData.data.map(({ tissueSiteDetailId, data }) => ({
    values: data.sort(),
    median: median(data),
    label: tissueLookup[tissueSiteDetailId]?.tissueSiteDetail,
    color: `#${tissueLookup[tissueSiteDetailId]?.colorHex}`,
  }))
  violinPlotData.sort(compareObjects('label'))
  renderViolinPlot(violinPlotData, containerElement)
}

export default props => (
  <GtexLauncher renderGtex={renderGtex} fetchAdditionalData={loadTissueData} {...props} />
)
