import React from 'react'
import { deviation, extent, max, mean, median, min, quantile } from 'd3-array'
import { randomNormal } from 'd3-random'
import { scaleBand, scaleLinear, scaleSequential } from 'd3-scale'
import { interpolatePurples } from 'd3-scale-chromatic'
import { area } from 'd3-shape'

import { initializeD3, Tooltip } from './d3Utils'
import GtexLauncher, { queryGtex } from './GtexLauncher'

const MARGINS = {
  top: 10,
  right: 50,
  bottom: 150,
}
const WIDTH = window.innerWidth * 0.8
const VIOLIN_HEIGHT = 400

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
    .range([scale.x(entry.tissue), scale.x(entry.tissue) + scale.x.bandwidth()])

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
      `${entry.tissue}<br/>Sample size: ${entry.values.length}<br/>Median TPM: ${entry.median.toPrecision(4)}<br/>`,
      x + 70,
      medianY < 40 ? 10 : medianY - 40,
    )
  })
  violinG.on('mouseout', () => {
    vPath.style('opacity', 0.6)
  })
}

const getViolinScales = violinPlotData => ({
  scales: {
    y: scaleLinear()
      .rangeRound([VIOLIN_HEIGHT, 0])
      .domain(extent(violinPlotData.reduce((acc, { values }) => ([...acc, ...values]), []))),
    z: scaleLinear(), // the violin width, domain and range are determined later individually for each violin
  },
  height: VIOLIN_HEIGHT,
  left: 50,
})
const getViolinAxis = scale => ({
  y: {
    text: 'TPM',
    transform: yAxis => yAxis.tickValues(scale.y.ticks(5)),
  },
})

// Code adapted from https://github.com/broadinstitute/gtex-viz/blob/f9d18299b2bcb69e4a919a4afa359c99a33fbc3b/src/TranscriptBrowser.js
// and https://github.com/broadinstitute/gtex-viz/blob/f9d18299b2bcb69e4a919a4afa359c99a33fbc3b/src/modules/Heatmap.js

const parseIsoformExpressionData = ({ median: medianValue, transcriptId }) => ({
  value: Number(medianValue), transcriptId,
})

const getIsoformScales = (isoformData) => {
  const yDomain = Object.entries(isoformData.reduce(
    (acc, { transcriptId, value }) => ({ ...acc, [transcriptId]: (acc[transcriptId] || 0) + value }), {},
  )).sort((a, b) => a[1] - b[1]).map(([transcriptId]) => transcriptId)

  const height = yDomain.length * 15

  const scales = {
    y: scaleBand()
      .rangeRound([height, 0])
      .domain(yDomain)
      .paddingInner(0.1),
    color: scaleSequential(interpolatePurples)
      .domain([0, max(isoformData.map(({ value }) => Math.log10(value + 1)))]),
  }
  return { scales, height, left: 100 }
}

const drawIsoformCell = (svg, scale, tooltip) => ({ tissue, transcriptId, value }) => {
  svg.append('rect')
    .attr('x', scale.x(tissue))
    .attr('y', scale.y(transcriptId))
    .attr('rx', 5)
    .attr('ry', 5)
    .attr('width', scale.x.bandwidth())
    .attr('height', scale.y.bandwidth())
    .style('fill', '#eeeeee')
    .on('mouseover', () => {
      tooltip.show(`Tissue: ${tissue}<br/> Isoform: ${transcriptId}<br/> TPM: ${value}`, scale.x(tissue), scale.y(transcriptId))
    })
    .on('mouseout', () => {
      tooltip.hide()
    })
    .style('fill', scale.color(Math.log10(value + 1)))
}

// seqr-specific code

const loadTissueData = onSuccess => queryGtex('dataset/tissueSiteDetail', {}, onSuccess)

const renderGtex = (
  responseKey, parseExpressionData, renderDataPoint, getScales, getAxis,
) => (expressionData, tissueData, containerElement) => {
  if (((expressionData || {})[responseKey] || []).length < 1) {
    return
  }
  const tissueLookup = tissueData.data.reduce(
    (acc, { tissueSiteDetailId, ...data }) => ({ ...acc, [tissueSiteDetailId]: data }), {},
  )
  const plotData = expressionData[responseKey].map(({ tissueSiteDetailId, ...data }) => ({
    ...parseExpressionData(data, tissueLookup[tissueSiteDetailId]),
    tissue: tissueLookup[tissueSiteDetailId]?.tissueSiteDetail,
  }))
  const xDomain = plotData.map(({ tissue }) => tissue).sort()
  const { scales, height, left } = getScales(plotData)
  const dimensions = { width: WIDTH, height }
  const margins = { ...MARGINS, left }
  const scale = {
    x: scaleBand()
      .rangeRound([0, WIDTH])
      .domain(xDomain)
      .paddingInner(0.2),
    ...scales,
  }
  const svg = initializeD3(containerElement, dimensions, margins, scale, getAxis ? getAxis(scale) : {})
  const tooltip = new Tooltip(containerElement)
  plotData.forEach(renderDataPoint(svg, scale, tooltip))
}

const parseViolinExpressionData = ({ data }, tissue) => ({
  values: data.sort(),
  median: median(data),
  color: `#${(tissue || {}).colorHex}`,
})
const renderGtexViolin = renderGtex('data', parseViolinExpressionData, drawViolin, getViolinScales, getViolinAxis)

const renderGtexIsoform = renderGtex('medianTranscriptExpression', parseIsoformExpressionData, drawIsoformCell, getIsoformScales)

const GtexViolin = props => (
  <GtexLauncher renderGtex={renderGtexViolin} fetchAdditionalData={loadTissueData} {...props} />
)

const GtexIsoform = props => (
  <GtexLauncher
    renderGtex={renderGtexIsoform}
    fetchAdditionalData={loadTissueData}
    expressionPath="clusteredMedianTranscriptExpression"
    {...props}
  />
)

export default GtexViolin
