// Code adapted from https://github.com/broadinstitute/gtex-viz/blob/8d65862fbe7e5ab9b4d5be419568754e0d17bb07/src/modules/Tooltip.js

export class Tooltip { // eslint-disable-line import/prefer-default-export

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
