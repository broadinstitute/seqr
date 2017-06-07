import React from 'react'
import PropTypes from 'prop-types'

export const InfoBox = (props) => {
  if (props.isVisible !== undefined && !props.isVisible) {
    return null
  }
  return <div>
    <span style={{ display: 'inline-block', padding: '3px 0px' }}><b>{props.label}:</b></span>
    {
      props.rightOfLabel && <span style={{ paddingLeft: '20px' }}>{props.rightOfLabel}</span>
    }
    {
      (props.showChildren === undefined || props.showChildren) &&
      <div style={{ display: 'block', padding: `0px 0px 10px ${props.leftPadding !== undefined ? props.leftPadding : 20}px` }}>
        {props.children}
      </div>
    }
  </div>
}

InfoBox.propTypes = {
  isVisible: PropTypes.any,
  showChildren: PropTypes.any,
  label: PropTypes.string.isRequired,
  //leftIcon: PropTypes.object,
  leftPadding: PropTypes.number,
  rightOfLabel: PropTypes.node,
  children: PropTypes.any.isRequired,
}


export const InfoLine = (props) => {
  if (props.isVisible !== undefined && !props.isVisible) {
    return null
  }
  return <div style={{ whiteSpace: 'nowrap' }}><div style={{ display: 'inline-block', padding: '5px 15px 5px 0px' }}><b>{props.label}: </b></div>{props.children}</div>
}

InfoLine.propTypes = {
  isVisible: PropTypes.any,
  label: PropTypes.string.isRequired,
  //leftIcon: PropTypes.object,
  //rightIcons: PropTypes.array,
  children: PropTypes.any.isRequired,
}
