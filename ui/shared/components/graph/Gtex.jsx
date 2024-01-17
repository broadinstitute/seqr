import React from 'react'
import styled from 'styled-components'
import { median } from 'd3-array'
import GroupedViolin from 'gtex-d3/src/modules/GroupedViolin' // TODO move into repo
import 'gtex-d3/css/violin.css'

import { compareObjects } from 'shared/utils/sortUtils'
import GtexLauncher, { queryGtex } from './GtexLauncher'

// TODO add attibution for open source code

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

const renderGtex = (expressionData, tissueData, containerElement) => {
  if ((expressionData?.data || []).length < 1) {
    return
  }
  const tissueLookup = tissueData.data.reduce(
    (acc, { tissueSiteDetailId, ...data }) => ({ ...acc, [tissueSiteDetailId]: data }), {},
  )
  const violinPlotData = expressionData.data.map(({ tissueSiteDetailId, data }) => ({
    values: data,
    // TODO sort values needed?
    median: median(data),
    group: tissueLookup[tissueSiteDetailId]?.tissueSiteDetail,
    color: tissueLookup[tissueSiteDetailId]?.colorHex,
  }))
  const violinPlot = new GroupedViolin(violinPlotData)

  violinPlot.createTooltip('')

  violinPlot.unit = ` ${expressionData.data[0].unit}`

  violinPlotData.sort(compareObjects('group'))
  const xDomain = violinPlotData.map(({ group }) => group)

  const svg = containerElement.append('svg')
    .attr('width', DIMENSIONS.w + MARGINS.left + MARGINS.right)
    .attr('height', DIMENSIONS.h + MARGINS.top + MARGINS.bottom)
    .append('g')
    .attr('transform', `translate(${MARGINS.left}, ${MARGINS.top})`)

  violinPlot.render(
    svg, DIMENSIONS.w, DIMENSIONS.h, 0.2, xDomain, [], 'TPM', true, 35,
    false, 0, false, false, true, false, true, true,
  )

  // update outlier display - TODO needed?
  svg.selectAll('path.violin').classed('outlined', false)
  svg.selectAll('.violin-outliers').toggle(true)

  svg.select('#violinLegend').remove()
  const xAxis = svg.select('.violin-x-axis')
  xAxis.attr('transform', `${xAxis.attr('transform')} translate(0, 3)`)
  const xAxisText = xAxis.selectAll('text')
  xAxisText.attr('transform', `translate(0, 8) ${xAxisText.attr('transform')}`)

  svg.selectAll('.violin-g').on('mouseover', (d, i, nodes) => {
    svg.select(nodes[i]).select('path').classed('highlighted', true)
    violinPlot.tooltip.show(
      `${d.group}<br/>Sample size: ${d.values.length})<br/>Median TPM: ${d.median.toPrecision(4)}<br/>`,
    )
  })
}

const loadTissueData = onSuccess => queryGtex('dataset/tissueSiteDetail', {}, onSuccess)

export default props => (
  <GtexContainer>
    <GtexLauncher renderGtex={renderGtex} fetchAdditionalData={loadTissueData} {...props} />
  </GtexContainer>
)
