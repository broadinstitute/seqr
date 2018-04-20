import React from 'react'
import PropTypes from 'prop-types'
import { Segment } from 'semantic-ui-react'
import { ScatterplotChart } from 'react-easy-chart'

const COLORS = [
  '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
]

const MIN_EXPONENT = -3.2
const MAX_EXPONENT = 3.2

const tissueName = (tissue) => {
  if (tissue.includes('-')) {
    const split = tissue.split('-')
    tissue = split[0].replace('_', ':_') + split.pop().split('_').pop()
  }
  return tissue.split('_').map(word => word[0].toUpperCase() + word.slice(1)).join(' ')
}

const xcoord = (d) => {
  // convert to base 2
  let e = Math.log(d) / Math.log(10)
  // don't allow outside bounds
  if (e < MIN_EXPONENT) e = MIN_EXPONENT
  if (e > MAX_EXPONENT) e = MAX_EXPONENT
  return e
}

const GeneExpression = ({ expression }) => {
  if (!expression) {
    return <p>Expression data not available for this gene.</p>
  }

  const tissues = Object.keys(expression).sort()
  const data = tissues.reduce((acc, tissue) =>
    acc.concat(expression[tissue].filter(d => d > 0).map((d) => { return {
      x: xcoord(d),
      y: tissueName(tissue),
      type: tissue,
    } }),
    ), [])
  const config = tissues.map((tissue, i) => { return { type: tissue, color: COLORS[i % COLORS.length] } })

  return (
    <Segment padded>
      <ScatterplotChart
        axes
        yType="text"
        width={1200}
        height={750}
        data={data}
        config={config}
        xDomainRange={[MIN_EXPONENT, MAX_EXPONENT]}
        axisLabels={{ x: 'LOG 10 EXPRESSION' }}
        style={{
          // Make dots more transparent
          '.dot': { opacity: 0.12 },
          // Hide unwanted axis lines
          '.axis path': { display: 'none' },
          '.x .tick-circle': { display: 'none' },
          // Move x axis to top and format text
          '.x.axis, .x.axis .label': { transform: 'translate(0, -20px)', opacity: 0.5, 'font-size': '11px', 'font-weight': '600', fill: 'black' },
          '.x.axis .label': { transform: 'translate(-790px, 6px)', opacity: 1 },
          // Format y axis
          '.y.axis': { 'font-size': '14px', 'font-weight': '600' },
          '.y .tick-circle': { r: '4px', opacity: 0.7 },
          // Make y axis tick circles match the dot color
          ...config.reduce((acc, cfg, i) => {
            return { [`.y g:nth-child(${i + 2}) .tick-circle`]: { fill: cfg.color }, ...acc }
          }, {}),
        }}
        margin={{ top: 24, right: 24, bottom: 0, left: 400 }}
      />
    </Segment>
  )
}

GeneExpression.propTypes = {
  expression: PropTypes.object,
}

export default GeneExpression
