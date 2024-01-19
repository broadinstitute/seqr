import { axisBottom, axisLeft } from 'd3-axis'

export const initializeD3 = (containerElement, dimensions, margins, scales, axis) => {
  const svg = containerElement.append('svg')
    .attr('width', dimensions.width + margins.left + margins.right)
    .attr('height', dimensions.height + margins.top + margins.bottom + (axis.x?.text ? 20 : 0))
    .append('g')
    .attr('transform', `translate(${margins.left}, ${margins.top})`)

  // render x-axis
  const buffer = 10
  let xAxis = axisBottom(scales.x)
  if (axis.x?.transform) {
    xAxis = axis.x.transform(xAxis)
  }
  const xAxisElement = svg.append('g')
    .attr('transform', `translate(${axis.x?.offset || 0}, ${dimensions.height}) translate(0, 3)`)
    .call(xAxis)
  // x-axis label
  if (axis.x?.text) {
    svg.append('text')
      .attr('text-anchor', 'end')
      .attr('transform', `translate(${dimensions.width / 2}, ${dimensions.height + margins.bottom + buffer})`)
      .text(axis.x.text)
  } else {
    xAxisElement.selectAll('text')
      .attr('text-anchor', 'start')
      .attr('transform', 'translate(0, 8) rotate(35, -10, 10)')
  }

  // render y-axis
  let yAxis = axisLeft(scales.y)
  if (axis.y.transform) {
    yAxis = axis.y.transform(yAxis)
  }
  svg.append('g')
    .attr('transform', `translate(-${buffer / 2}, 0)`)
    .call(yAxis)
  // y-axis label
  svg.append('text')
    .attr('text-anchor', 'middle')
    .attr('transform', `translate(${buffer - margins.left}, ${dimensions.height / 2}) rotate(-90)`)
    .text(axis.y.text)

  return svg
}

// Code adapted from https://github.com/broadinstitute/gtex-viz/blob/8d65862fbe7e5ab9b4d5be419568754e0d17bb07/src/modules/Tooltip.js

export class Tooltip {

  constructor(containerElement) {
    this.tooltip = containerElement.append('div')
      .style('display', 'none')
      .style('position', 'absolute')
      .style('background-color', 'rgba(32, 53, 73, 0.95)')
      .style('color', '#ffffff')
      .style('padding', '10px')
      .style('min-width', '50px')
      .style('font-size', '12px')
      .style('border-radius', '5px')
      .style('z-index', '4000')

    containerElement.on('mouseout', () => {
      this.hide()
    })
  }

    show = (html, left, top) => this.tooltip.html(html)
      .style('display', 'inline')
      .style('left', `${left}px`)
      .style('top', `${top}px`)

    hide = () => this.tooltip.style('display', 'none')

}
