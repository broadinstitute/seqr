import React from 'react'
import PropTypes from 'prop-types'
import { extent, max, median, min, quantile } from 'd3-array'
import { scaleBand, scaleLinear } from 'd3-scale'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { TISSUE_DISPLAY } from 'shared/utils/constants'
import { initializeD3, Tooltip } from 'shared/components/graph/d3Utils'
import GtexLauncher from 'shared/components/graph/GtexLauncher'

const BOX_WIDTH = 100
const PLOT_WIDTH = 550
const PLOT_HEIGHT = 350
const MARGINS = {
  left: 40,
  top: 0,
  bottom: 100,
}

// Code adapted from https://github.com/broadinstitute/gtex-viz/blob/8d65862fbe7e5ab9b4d5be419568754e0d17bb07/src/modules/Boxplot.js

const renderBoxplot = (allData, containerElement) => {
  const boxplotData = allData.map(({ data, ...d }) => {
    const q1 = quantile(data, 0.25)
    const q3 = quantile(data, 0.75)
    const iqr = q3 - q1
    const upperBound = max(data.filter(x => x <= q3 + (1.5 * iqr)))
    const lowerBound = min(data.filter(x => x >= q1 - (1.5 * iqr)))
    return {
      ...d,
      q1,
      q3,
      upperBound,
      lowerBound,
      data: data.sort(),
      color: 'efefef',
      median: median(data),
      outliers: data.filter(x => x < lowerBound || x > upperBound),
    }
  })

  const width = Math.min(BOX_WIDTH * boxplotData.length, PLOT_WIDTH)

  const yDomain = extent(boxplotData.reduce((acc, { data }) => ([...acc, ...data]), []))
  const scales = {
    x: scaleBand()
      .domain(boxplotData.map(d => d.label))
      .range([0, width])
      .paddingInner(0.2),
    y: scaleLinear()
      .domain(yDomain)
      .range([PLOT_HEIGHT, 0]),
  }
  const bandwidth = scales.x.bandwidth()

  const svg = initializeD3(
    containerElement,
    { width: PLOT_WIDTH, height: PLOT_HEIGHT },
    { ...MARGINS, right: bandwidth / 2 + 10 },
    scales,
    { x: { offset: bandwidth / 2 }, y: { text: 'TPM' } },
  )

  // render IQR box
  const tooltip = new Tooltip(containerElement)
  const box = svg.append('g')
    .attr('transform', `translate(${bandwidth}, 0)`)
    .selectAll('rect')
    .data(boxplotData)
    .enter()
    .append('rect')
    .attr('x', d => scales.x(d.label) - bandwidth / 2)
    .attr('y', d => scales.y(d.q3))
    .attr('width', () => bandwidth)
    .attr('height', d => Math.abs(scales.y(d.q1) - scales.y(d.q3)))
    .attr('fill', d => `#${d.color}`)
    .attr('stroke', '#aaa')
  box.on('mouseover', (d) => {
    tooltip.show(
      `${d.label}<br/>Sample size: ${d.data.length}<br/>Median TPM: ${d.median.toPrecision(3)}<br/>`,
      scales.x(d.label),
      scales.y(d.median),
    )
  }).on('mouseout', () => {
    tooltip.hide()
  })

  // render median
  svg.append('g')
    .attr('transform', `translate(${bandwidth}, 0)`)
    .selectAll('line')
    .data(boxplotData)
    .enter()
    .append('line')
    .attr('x1', d => scales.x(d.label) - bandwidth / 2)
    .attr('y1', d => scales.y(d.median))
    .attr('x2', d => scales.x(d.label) + bandwidth / 2)
    .attr('y2', d => scales.y(d.median))
    .attr('stroke', d => d.medianColor || '#000')
    .attr('stroke-width', 2)

  const whiskers = svg.append('g')
  // render high whisker
  whiskers.append('g')
    .attr('transform', `translate(${bandwidth}, 0)`)
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
    .attr('transform', `translate(${bandwidth}, 0)`)
    .selectAll('line')
    .data(boxplotData)
    .enter()
    .append('line')
    .attr('x1', d => scales.x(d.label) - bandwidth / 4)
    .attr('y1', d => scales.y(d.upperBound))
    .attr('x2', d => scales.x(d.label) + bandwidth / 4)
    .attr('y2', d => scales.y(d.upperBound))
    .attr('stroke', '#aaa')

  // render low whisker
  whiskers.append('g')
    .attr('transform', `translate(${bandwidth}, 0)`)
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
    .attr('transform', `translate(${bandwidth}, 0)`)
    .selectAll('line')
    .data(boxplotData)
    .enter()
    .append('line')
    .attr('x1', d => scales.x(d.label) - bandwidth / 4)
    .attr('y1', d => scales.y(d.lowerBound))
    .attr('x2', d => scales.x(d.label) + bandwidth / 4)
    .attr('y2', d => scales.y(d.lowerBound))
    .attr('stroke', '#aaa')

  // render outliers
  const outliers = svg.append('g')
    .attr('transform', `translate(${bandwidth}, 0)`)
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
  const gtexByTissue = ((gtexExpressionData || {}).data || []).reduce((acc, { data, tissueSiteDetailId }) => ({
    ...acc, [GTEX_TISSUE_LOOKUP[tissueSiteDetailId]]: data,
  }), {})
  const boxplotData = Object.entries(familyExpressionData).reduce((acc, [tissue, { rdgData, individualData }]) => ([
    ...acc,
    ...[
      { data: gtexByTissue[tissue], label: 'GTEx' },
      { data: rdgData, label: 'RDG' },
      ...Object.entries(individualData).map(([individual, tpm]) => ({ data: [tpm], label: individual, medianColor: '#000080' })),
    ].filter(({ data }) => data).map(({ label, ...d }) => ({ label: `${label} - ${TISSUE_DISPLAY[tissue]}`, ...d })),
  ]), [])
  renderBoxplot(boxplotData, containerElement)
}

const RnaSeqTpm = ({ geneId, familyGuid }) => (
  <GtexLauncher
    geneId={geneId}
    renderGtex={renderGtex}
    fetchAdditionalData={loadFamilyRnaSeq(geneId, familyGuid)}
    getAdditionalExpressionParams={parseGtexTissue}
    renderOnError
  />
)

RnaSeqTpm.propTypes = {
  geneId: PropTypes.string.isRequired,
  familyGuid: PropTypes.string.isRequired,
}

export default RnaSeqTpm
