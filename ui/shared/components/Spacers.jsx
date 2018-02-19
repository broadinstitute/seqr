import React from 'react'
import PropTypes from 'prop-types'

export const HorizontalSpacer = props =>
  <div style={{ display: 'inline-block', width: `${props.width}px` }} />

HorizontalSpacer.propTypes = {
  width: PropTypes.number,
}


export const VerticalSpacer = props =>
  <div style={{ height: `${props.height}px` }} />

VerticalSpacer.propTypes = {
  height: PropTypes.number,
}
