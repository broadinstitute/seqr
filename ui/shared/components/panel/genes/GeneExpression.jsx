import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Segment, Popup } from 'semantic-ui-react'
import { ScatterplotChart } from 'react-easy-chart'

import { snakecaseToTitlecase } from '../../../utils/stringUtils'

const FixedPositionPopup = styled(Popup)`
  top: ${props => props.top - 90}px !important;
  left: ${props => props.left - 20}px !important;
  right: unset !important;

  :before {
    bottom: -0.37em;
  }
`

const COLORS = [
  '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
]

const MIN_EXPONENT = -3.2
const MAX_EXPONENT = 3.2
const RANGE = [MIN_EXPONENT, MAX_EXPONENT]
const X_LABELS = { x: 'LOG 10 EXPRESSION' }
const MARGIN = { top: 24, right: 24, bottom: 0, left: 400 }

const STYLE = {
  // Make dots more transparent
  '.dot': { opacity: 0.12 },
  // Hide unwanted axis lines
  '.axis path': { display: 'none' },
  '.x .tick-circle': { display: 'none' },
  // Move x axis to top and format text
  '.x.axis, .x.axis .label': {
    transform: 'translate(0, -20px)',
    opacity: 0.5,
    'font-size': '11px',
    'font-weight': '600',
    fill: 'black',
  },
  '.x.axis .label': { transform: 'translate(-790px, 6px)', opacity: 1 },
  // Format y axis
  '.y.axis': { 'font-size': '14px', 'font-weight': '600' },
  '.y .tick-circle': { r: '4px', opacity: 0.7 },
  // Make y axis tick circles match the dot color
  ...Array.from({ length: 50 }, (o, i) => COLORS[i % COLORS.length]).reduce((acc, color, i) => {
    return { [`.y g:nth-child(${i + 2}) .tick-circle`]: { fill: color }, ...acc }
  }, {}),
}

const tissueName = (tissue) => {
  if (tissue.includes('-')) {
    const split = tissue.split('-')
    tissue = split[0].replace('_', ':_') + split.pop().split('_').pop()
  }
  return snakecaseToTitlecase(tissue)
}

const xcoord = (d) => {
  // convert to base 2
  let e = Math.log(d) / Math.log(10)
  // don't allow outside bounds
  if (e < MIN_EXPONENT) e = MIN_EXPONENT
  if (e > MAX_EXPONENT) e = MAX_EXPONENT
  return e
}

class GeneExpression extends React.PureComponent {

  constructor(props) {
    super(props)

    this.state = {
      popupOpen: false,
      hoverData: { x: 0, y: 0, sampleCount: 0 },
      hoverPostiton: { pageX: 0, pageY: 0 },
    }
  }

  mouseOverHandler = (d, e) => {
    this.setState({
      popupOpen: true,
      hoverData: d,
      hoverPostiton: e,
    })
  }

  mouseOutHandler = () => {
    // this.setState({ popupOpen: false })
  }

  render() {
    const { expression } = this.props
    if (!expression) {
      return <p>Expression data not available for this gene.</p>
    }

    const tissues = Object.keys(expression).sort()
    const tissueExpression = tissues.reduce((acc, tissue) =>
      ({ ...acc, [tissue]: expression[tissue].filter(d => d > 0) }), {},
    )
    const data = tissues.reduce((acc, tissue) =>
      acc.concat(tissueExpression[tissue].map(d => ({
        x: xcoord(d),
        y: tissueName(tissue),
        type: tissue,
        sampleCount: tissueExpression[tissue].length,
      }))), [],
    )
    const config = tissues.map((tissue, i) => {
      return { type: tissue, color: COLORS[i % COLORS.length] }
    })

    return (
      <Segment padded>
        <FixedPositionPopup
          open={this.state.popupOpen}
          header={this.state.hoverData.y}
          content={
            <span>
              {this.state.hoverData.sampleCount} samples<br />
              {this.state.hoverData.x.toFixed(2)} log<sub>10</sub>RPKM
            </span>
          }
          top={this.state.hoverPostiton.pageY}
          left={this.state.hoverPostiton.pageX}
          size="small"
        />
        <ScatterplotChart
          axes
          yType="text"
          width={1200}
          height={750}
          data={data}
          config={config}
          xDomainRange={RANGE}
          axisLabels={X_LABELS}
          style={STYLE}
          margin={MARGIN}
          mouseOverHandler={this.mouseOverHandler}
          mouseOutHandler={this.mouseOutHandler}
          mouseMoveHandler={this.mouseOverHandler}
        />
      </Segment>
    )
  }
}

GeneExpression.propTypes = {
  expression: PropTypes.object,
}

export default GeneExpression
