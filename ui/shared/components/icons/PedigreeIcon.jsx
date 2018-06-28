/* eslint-disable indent */

import React from 'react'
import PropTypes from 'prop-types'

import { Icon, Popup } from 'semantic-ui-react'

import { SEX_LOOKUP, AFFECTED_LOOKUP } from 'shared/utils/constants'

const iconStyle = { fontSize: '13px !important' }
const rotate45deg = {
  msTransform: 'rotate(45deg)', /* IE 9 */
  WebkitTransform: 'rotate(45deg)', /* Chrome, Safari, Opera */
  transform: 'rotate(45deg)',
  fontSize: '0.85em',
  ...iconStyle,
}

const ICON_LOOKUP = {

  MA: { icon: 'square' },
  MN: { icon: 'square outline' },
  MU: {
    iconGroup: (
      <Icon.Group>
        <Icon style={iconStyle} name="square outline" />
        <Icon size="small" name="question" />
      </Icon.Group>
    ),
  },

  FA: { icon: 'circle' },
  FN: { icon: 'circle thin' },
  FU: { icon: 'question circle outline' },

  UA: { icon: 'square', rotated: true },
  UN: { icon: 'square outline', rotated: true },
  UU: { icon: 'help' },
}

const PedigreeIcon = (props) => {
  const iconProps = ICON_LOOKUP[`${props.sex}${props.affected}`]
  return <Popup
    trigger={iconProps.iconGroup || <span><Icon style={iconProps.rotate ? rotate45deg : iconStyle} name={iconProps.icon || 'warning sign'} />{props.label}</span>}
    content={
      <div>
        <b>Sex:</b> {SEX_LOOKUP[props.sex] || 'INVALID'} <br />
        <b>Status:</b> {AFFECTED_LOOKUP[props.affected] || 'INVALID'}
        {props.popupContent}
      </div>
    }
    size="small"
    wide="very"
    position="top center"
    hoverable
  />
}


PedigreeIcon.propTypes = {
  sex: PropTypes.string.isRequired,
  affected: PropTypes.string.isRequired,
  popupContent: PropTypes.node,
  label: PropTypes.any,
}

export default PedigreeIcon
