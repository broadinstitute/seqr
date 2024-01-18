import React from 'react'
import PropTypes from 'prop-types'
import { extent, max, median, min, quantile } from 'd3-array'
import { axisBottom, axisLeft } from 'd3-axis'
import { scaleBand, scaleLinear } from 'd3-scale'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { TISSUE_DISPLAY } from 'shared/utils/constants'
import { compareObjects } from 'shared/utils/sortUtils'
import GtexLauncher from '../../graph/GtexLauncher'
import 'gtex-d3/css/boxplot.css' // TODO remove

const PLOT_WIDTH = 600
const PLOT_HEIGHT = 450
const AXIS_FONT_SIZE = 11
const MARGINS = {
  top: 0,
  bottom: 100,
  left: 40,
}

// Code adapted from https://github.com/broadinstitute/gtex-viz/blob/8d65862fbe7e5ab9b4d5be419568754e0d17bb07/src/modules/Boxplot.js

const renderBoxplot = (allData, containerElement, marginRight) => {
  const boxplotData = allData.sort(compareObjects('label')).map(({ data, color, label }) => {
    const q1 = quantile(data, 0.25)
    const q3 = quantile(data, 0.75)
    const iqr = q3 - q1
    const upperBound = max(data.filter(x => x <= q3 + (1.5 * iqr)))
    const lowerBound = min(data.filter(x => x >= q1 - (1.5 * iqr)))
    return {
      color,
      label,
      q1,
      q3,
      upperBound,
      lowerBound,
      data: data.sort(),
      median: median(data),
      outliers: data.filter(x => x < lowerBound || x > upperBound),
    }
  })

  //  createTooltip(tooltipId) // TODO

  const svg = containerElement.append('svg')
    .attr('width', PLOT_WIDTH)
    .attr('height', 450)

  const dom = svg.append('g')
    .attr('id', 'gtex-viz-boxplot') // TODO remove unneccessary ids/ classes

  const yDomain = extent(boxplotData.reduce((acc, { data }) => ([...acc, ...data]), []))
  const scales = {
    x: scaleBand()
      .domain(boxplotData.map(d => d.label))
      .range([0, PLOT_WIDTH - (MARGINS.left + marginRight)])
      .paddingInner(0.35),
    y: scaleLinear()
      .domain(yDomain)
      .range([PLOT_HEIGHT - (MARGINS.top + MARGINS.bottom), 0]),
  }

  const xAxis = axisBottom(scales.x)
  const yAxis = axisLeft(scales.y)

  // render x-axis
  dom.append('g')
    .attr('class', 'boxplot-x-axis')
    .attr('transform', `translate(${MARGINS.left + scales.x.bandwidth() / 2}, ${PLOT_HEIGHT - MARGINS.bottom})`)
    .call(xAxis)
    .attr('text-anchor', 'start')
    .selectAll('text')
    .attr('transform', 'translate(5,1) rotate(45)')
    .attr('font-size', 12)
  // x-axis label
  dom.append('text')
    .attr('transform', `translate(${MARGINS.left + PLOT_WIDTH / 2 + scales.x.bandwidth() / 2}, ${PLOT_HEIGHT - AXIS_FONT_SIZE / 2})`)
    .attr('text-anchor', 'middle')
    .style('font-size', AXIS_FONT_SIZE)
    .text('') // TODO axis needed at all?

  // render y-axis
  dom.append('g')
    .attr('class', 'boxplot-y-axis')
    .attr('transform', `translate(${MARGINS.left}, ${MARGINS.top})`)
    .call(yAxis)
    .attr('font-size', AXIS_FONT_SIZE)
  // y-axis label
  dom.append('text')
    .attr('transform', `translate(${AXIS_FONT_SIZE}, ${(PLOT_HEIGHT - MARGINS.bottom) / 2}) rotate(270)`)
    .attr('text-anchor', 'middle')
    .style('font-size', AXIS_FONT_SIZE)
    .text('TPM')

  // render IQR box
  dom.append('g')
    .attr('class', 'boxplot-iqr')
    .attr('transform', `translate(${MARGINS.left + scales.x.bandwidth()}, ${MARGINS.top})`)
    .selectAll('rect')
    .data(boxplotData)
    .enter()
    .append('rect')
    .attr('x', d => scales.x(d.label) - scales.x.bandwidth() / 2)
    .attr('y', d => scales.y(d.q3))
    .attr('width', () => scales.x.bandwidth())
    .attr('height', d => Math.abs(scales.y(d.q1) - scales.y(d.q3))) // TODO not displaying properly, needed to add Math.abs, probs related to violin issue
    .attr('fill', d => `#${d.color}`)
    .attr('stroke', '#aaa')
    // .on('mouseover', (d, i, nodes) => {
    //     let selectedDom = select(nodes[i]);
    //     this.boxplotMouseover(d, selectedDom);
    // })
    // .on('mouseout', (d, i, nodes) => {
    //     let selectedDom = select(nodes[i]);
    //     this.boxplotMouseout(d, selectedDom);
    // })  // TODO

  // render median
  dom.append('g')
    .attr('class', 'boxplot-median')
    .attr('transform', `translate(${MARGINS.left + scales.x.bandwidth()}, ${MARGINS.top})`)
    .selectAll('line')
    .data(boxplotData)
    .enter()
    .append('line')
    .attr('x1', d => scales.x(d.label) - scales.x.bandwidth() / 2)
    .attr('y1', d => scales.y(d.median))
    .attr('x2', d => scales.x(d.label) + scales.x.bandwidth() / 2)
    .attr('y2', d => scales.y(d.median))
    .attr('stroke', '#000')
    .attr('stroke-width', 2)

  const whiskers = dom.append('g')
    .attr('class', 'boxplot-whisker')
  // render high whisker
  whiskers.append('g')
    .attr('transform', `translate(${MARGINS.left + scales.x.bandwidth()}, ${MARGINS.top})`)
    .selectAll('line')
    .data(boxplotData)
    .enter()
    .append('line')
    .attr('x1', d => scales.x(d.label))
    .attr('y1', d => scales.y(d.q3))
    .attr('x2', d => scales.x(d.label))
    .attr('y2', d => scales.y(d.upperBound))
    .attr('stroke', '#aaa')
  whiskers.append('g')
    .attr('transform', `translate(${MARGINS.left + scales.x.bandwidth()}, ${MARGINS.top})`)
    .selectAll('line')
    .data(boxplotData)
    .enter()
    .append('line')
    .attr('x1', d => scales.x(d.label) - scales.x.bandwidth() / 4)
    .attr('y1', d => scales.y(d.upperBound))
    .attr('x2', d => scales.x(d.label) + scales.x.bandwidth() / 4)
    .attr('y2', d => scales.y(d.upperBound))
    .attr('stroke', '#aaa')

  // render low whisker
  whiskers.append('g')
    .attr('transform', `translate(${MARGINS.left + scales.x.bandwidth()}, ${MARGINS.top})`)
    .selectAll('line')
    .data(boxplotData)
    .enter()
    .append('line')
    .attr('x1', d => scales.x(d.label))
    .attr('y1', d => scales.y(d.q1))
    .attr('x2', d => scales.x(d.label))
    .attr('y2', d => scales.y(d.lowerBound))
    .attr('stroke', '#aaa')
  whiskers.append('g')
    .attr('transform', `translate(${MARGINS.left + scales.x.bandwidth()}, ${MARGINS.top})`)
    .selectAll('line')
    .data(boxplotData)
    .enter()
    .append('line')
    .attr('x1', d => scales.x(d.label) - scales.x.bandwidth() / 4)
    .attr('y1', d => scales.y(d.lowerBound))
    .attr('x2', d => scales.x(d.label) + scales.x.bandwidth() / 4)
    .attr('y2', d => scales.y(d.lowerBound))
    .attr('stroke', '#aaa')

  // render outliers
  const outliers = dom.append('g')
    .attr('class', 'boxplot-outliers')
    .attr('transform', `translate(${MARGINS.left + scales.x.bandwidth()}, ${MARGINS.top})`)
    .selectAll('g')
    .data(boxplotData)
    .enter()
    .append('g')
  outliers.selectAll('circle')
    .data(d => d.outliers.map(x => ({ label: d.label, val: x })))
    .enter()
    .append('circle')
    .attr('cx', d => scales.x(d.label))
    .attr('cy', d => scales.y(d.val))
    .attr('r', '2')
    .attr('stroke', '#aaa')
    .attr('fill', 'none')
}

// seqr-specific code

const GTEX_TISSUES = {
  WB: 'Whole_Blood',
  F: 'Cells_Cultured_fibroblasts',
  M: 'Muscle_Skeletal',
  L: 'Cells_EBV-transformed_lymphocytes',
}

const GTEX_TISSUE_LOOKUP = Object.entries(GTEX_TISSUES).reduce((acc, [k, v]) => ({ ...acc, [v]: k }), {})

const loadFamilyRnaSeq = (geneId, familyGuid) => onSuccess => (
  new HttpRequestHelper(`/api/family/${familyGuid}/rna_seq_data/${geneId}`, onSuccess, () => {}).get()
)

const parseGtexTissue = familyExpressionData => ({
  tissueSiteDetailId: Object.keys(familyExpressionData).map(tissue => GTEX_TISSUES[tissue]),
})

const renderGtex = (gtexExpressionData, familyExpressionData, containerElement) => {
  const boxplotData = Object.entries(familyExpressionData).reduce((acc, [tissue, { rdgData, individualData }]) => ([
    ...acc,
    { label: `*RDG - ${TISSUE_DISPLAY[tissue]}`, color: 'efefef', data: rdgData },
    ...Object.entries(individualData).map(([individual, tpm]) => ({ label: individual, data: [tpm] })),
  ]), [])

  // TODO clean up
  const tissues = Object.keys(familyExpressionData)
  const numEntries = (tissues.length * 2) + boxplotData.length
  const marginRight = PLOT_WIDTH - MARGINS.left - (numEntries * 80)
  boxplotData.push(...gtexExpressionData.data.map(({ data, tissueSiteDetailId }) => (
    { data, label: `*GTEx - ${TISSUE_DISPLAY[GTEX_TISSUE_LOOKUP[tissueSiteDetailId]]}`, color: 'efefef' }
  )))
  renderBoxplot(boxplotData, containerElement, marginRight)
}

const RnaSeqTpm = ({ geneId, familyGuid }) => (
  <GtexLauncher
    geneId={geneId}
    renderGtex={renderGtex}
    fetchAdditionalData={loadFamilyRnaSeq(geneId, familyGuid)}
    getAdditionalExpressionParams={parseGtexTissue}
  />
)

RnaSeqTpm.propTypes = {
  geneId: PropTypes.string.isRequired,
  familyGuid: PropTypes.string.isRequired,
}

export default RnaSeqTpm
