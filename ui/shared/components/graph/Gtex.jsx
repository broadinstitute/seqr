import React from 'react'
import styled from 'styled-components'
import { extent, max, median, min, quantile } from 'd3-array'
import { axisBottom, axisLeft } from 'd3-axis'
import { randomNormal } from 'd3-random'
import { scaleBand, scaleLinear } from 'd3-scale'
import { area } from 'd3-shape'
import Tooltip from 'gtex-d3/src/modules/Tooltip' // TODO move into repo
import { kernelDensityEstimator, kernel, kernelBandwidth } from 'gtex-d3/src/modules/kde' // TODO move into repo
import 'gtex-d3/css/violin.css'

import { compareObjects } from 'shared/utils/sortUtils'
import GtexLauncher, { queryGtex } from './GtexLauncher'

// TODO add attibution for open source code 'gtex-d3/src/GeneExpressionViolinPlot'

const GtexContainer = styled.div`
  #gene-expression-plot-toolbar {
    margin-left: 100px;
    margin-top: 20px;
      
    .gene-expression-plot-option-label {
      padding-right: 5px;
      font-size: 15px;
      font-variant: all-small-caps;
      font-weight: 500;
    }
    
    .col-lg-1 {
        display: none !important;
    }
    .col-lg-2 {
        width: 20%;
        float: left;
    }
    .col-lg-11 {
        width: 100%;
    }
    
    .btn-group {
      display: inline-block;
      vertical-align: middle;
      
      .btn {
        padding: 5px 10px;
        font-size: 12px;
        line-height: 1.5;
        border-radius: 3px;
        cursor: pointer;
        user-select: none;
        border: 1px solid #ccc;
          
        &:first-child {
          border-top-right-radius: 0;
          border-bottom-right-radius: 0;
        }
          
        &:last-child {
          border-top-left-radius: 0;
          border-bottom-left-radius: 0;
        }
          
        &.active, &:active,  &:focus, &:hover {
          background-color: #e6e6e6;
          border-color: #adadad;
          box-shadow: inset 0 3px 5px rgba(0,0,0,.125);
        }
          
        &+.btn {
          margin-left: -1px;
        }
      }
    }
    
    .fa {
      font-family: 'Icons';
      font-style: normal;
      
      &.fa-caret-up:before {
        content: "\\f0d8";
      }
      &.fa-caret-down:before {
        content: "\\f0d7";
      } 
    }
  }
  
  #gene-expression-plot-svg {
    .violin-x-axis, .violin-y-axis {
      line, path {
        stroke: Black;
      }
    }
    
    .violin-x-axis text, .violin-y-axis text, text.violin-axis-label {
      fill: Black;
      font-size: 11.5px;
      font-weight: 500;
    }
  }
`

const MARGINS = {
  top: 10,
  right: 50,
  bottom: 150,
  left: 50,
}
const DIMENSIONS = {
  w: window.innerWidth * 0.8,
  h: 400,
}

// const launchGtexOld = (geneId) => {
//   launch(GTEX_CONTAINER_ID, `${GTEX_CONTAINER_ID}-tooltip`, geneId, '', URLS, MARGINS, DIMENSIONS)
// }

const drawViolin = (svg, scale, tooltip) => (entry) => {
  const kde = kernelDensityEstimator(
    kernel.gaussian,
    scale.y.ticks(100), // use up to 100 vertices along the Y axis (to create the violin path)
    kernelBandwidth.nrd(entry.values), // estimate the bandwidth based on the data
  )
  const eDomain = extent(entry.values) // get the max and min in entry.values
  // filter the vertices that aren't in the entry.values
  const vertices = kde(entry.values).filter(d => d[0] >= eDomain[0] && d[0] <= eDomain[1])

  const violinG = svg.append('g')
    .attr('class', 'violin-g') // TODO remove unused classes and ids
    .datum(entry)

  if (vertices.length < 1 || vertices.some(Number.isNaN)) {
    return
  }

  // define the z scale -- the violin width
  const zMax = max(vertices, d => Math.abs(d[1]))
  scale.z
    .domain([-zMax, zMax])
    .range([scale.x(entry.group), scale.x(entry.group) + scale.x.bandwidth()])

  // visual rendering
  const violin = area()
    .x0(d => scale.z(d[1]))
    .x1(d => scale.z(-d[1]))
    .y(d => scale.y(d[0]))

  const vPath = violinG.append('path')
    .datum(vertices)
    .attr('d', violin)
    .classed('violin', true)
    .classed('outlined', false)
    .style('fill', () => entry.color)

  // boxplot
  const q1 = quantile(entry.values, 0.25)
  const q3 = quantile(entry.values, 0.75)
  const z = scale.z.domain()[1] / 3

  // interquartile range
  violinG.append('rect')
    .attr('x', scale.z(-z))
    .attr('y', scale.y(q3))
    .attr('width', Math.abs(scale.z(-z) - scale.z(z)))
    .attr('height', Math.abs(scale.y(q3) - scale.y(q1)))
    .attr('class', 'violin-ir')

  // the median line
  violinG.append('line')
    .attr('x1', scale.z(-z))
    .attr('x2', scale.z(z))
    .attr('y1', scale.y(entry.median))
    .attr('y2', scale.y(entry.median))
    .attr('class', 'violin-median')

  const jitter = randomNormal(0, z / 2)
  const iqr = Math.abs(q3 - q1)
  const upper = max(entry.values.filter(d => d <= q3 + (iqr * 1.5)))
  const lower = min(entry.values.filter(d => d >= q1 - (iqr * 1.5)))
  const outliers = entry.values.filter(d => d < lower || d > upper)
  violinG.append('g')
    .attr('class', 'violin-outliers')
    .selectAll('circle')
    .data(outliers)
    .enter()
    .append('circle')
    .attr('cx', () => scale.z(jitter()))
    .attr('cy', d => scale.y(d))
    .attr('r', 2)

  // mouse events
  violinG.on('mouseover', () => {
    vPath.classed('highlighted', true)
    tooltip.show(
      `${entry.group}<br/>Sample size: ${entry.values.length})<br/>Median TPM: ${entry.median.toPrecision(4)}<br/>`,
    )
  })
  violinG.on('mouseout', () => {
    vPath.classed('highlighted', false)
  })
}

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
    group: tissueLookup[tissueSiteDetailId]?.tissueSiteDetail,
    color: tissueLookup[tissueSiteDetailId]?.colorHex,
  }))
  violinPlotData.sort(compareObjects('group'))
  console.log(violinPlotData)

  const svg = containerElement.append('svg')
    .attr('width', DIMENSIONS.w + MARGINS.left + MARGINS.right)
    .attr('height', DIMENSIONS.h + MARGINS.top + MARGINS.bottom)
    .append('g')
    .attr('transform', `translate(${MARGINS.left}, ${MARGINS.top})`)

  const tooltip = new Tooltip(containerElement.append('div').classed('violin-tooltip', true))

  const xDomain = violinPlotData.map(({ group }) => group)
  const yDomain = extent(violinPlotData.reduce((acc, { values }) => ([...acc, ...values]), []))

  const scale = {
    x: scaleBand()
      .rangeRound([0, DIMENSIONS.w])
      .domain(xDomain)
      .paddingInner(0.2),
    y: scaleLinear()
      .rangeRound([DIMENSIONS.h, 0])
      .domain(yDomain),
    z: scaleLinear(), // the violin width, domain and range are determined later individually for each violin
  }

  violinPlotData.forEach(drawViolin(svg, scale, tooltip))

  // renders the x axis
  svg.append('g')
    .attr('class', 'violin-x-axis axis--x')
    .attr('transform', `translate(0, ${DIMENSIONS.h}) translate(0, 3)`)
    .call(axisBottom(scale.x))
    .selectAll('text')
    .attr('text-anchor', 'start')
    .attr('transform', 'translate(0, 8) rotate(35, -10, 10)')

  // adds the y Axis
  const buffer = 5
  const yAxis = svg.append('g')
    .attr('class', 'violin-y-axis axis--y')
    .attr('transform', `translate(-${buffer}, 0)`)
    .call(axisLeft(scale.y).tickValues(scale.y.ticks(5)))

  // adds the text label for the y axis
  const yRange = scale.y.range()
  svg.append('text')
    .attr('class', 'violin-axis-label')
    .attr('text-anchor', 'middle')
    .attr('transform', `translate(-${buffer * 2 + yAxis.node().getBBox().width}, ${yRange[0] + (yRange[1] - yRange[0]) / 2}) rotate(-90)`)
    .text('TPM')

  // plot mouse events
  svg.on('mouseout', () => {
    tooltip.hide()
  })
}

const loadTissueData = onSuccess => queryGtex('dataset/tissueSiteDetail', {}, onSuccess)

export default props => (
  <GtexContainer>
    <GtexLauncher renderGtex={renderGtex} fetchAdditionalData={loadTissueData} {...props} />
  </GtexContainer>
)
