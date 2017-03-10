import React from 'react'


export const HorizontalSpacer = props =>
  <div style={{ display: 'inline-block', width: `${props.width}px` }} />

HorizontalSpacer.propTypes = {
  width: React.PropTypes.number,
}


export const VerticalSpacer = props =>
  <div style={{ height: `${props.height}px` }} />

VerticalSpacer.propTypes = {
  height: React.PropTypes.number,
}
