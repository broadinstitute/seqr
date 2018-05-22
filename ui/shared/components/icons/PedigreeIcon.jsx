/* eslint-disable indent */

import React from 'react'
import PropTypes from 'prop-types'

import { Icon, Popup } from 'semantic-ui-react'

const iconStyle = { fontSize: '13px !important' }
const rotate45deg = {
  msTransform: 'rotate(45deg)', /* IE 9 */
  WebkitTransform: 'rotate(45deg)', /* Chrome, Safari, Opera */
  transform: 'rotate(45deg)',
  fontSize: '0.85em',
  ...iconStyle,
}

const ICON_LOOKUP = {

  MA: <Popup trigger={<Icon style={iconStyle} name="square" />} content="affected male" size="small" />,
  MN: <Popup trigger={<Icon style={iconStyle} name="square outline" />} content="unaffected male" size="small" />,
  MU: <Popup
    trigger={
      <Icon.Group>
        <Icon style={iconStyle} name="square outline" />
        <Icon style={iconStyle} name="question" />
      </Icon.Group>
    }
    content="male with unknown affected status"
    size="small"
  />,

  FA: <Popup trigger={<Icon style={iconStyle} name="circle" />} content="affected female" size="small" />,
  FN: <Popup trigger={<Icon style={iconStyle} name="circle thin" />} content="unaffected female" size="small" />,
  FU: <Popup trigger={<Icon style={iconStyle} name="question circle outline" />} content="female with unknown affected status" size="small" />,

  UA: <Popup trigger={<Icon style={rotate45deg} name="square" />} content="affected inidividual with unknown sex" size="small" />,
  UN: <Popup trigger={<span style={rotate45deg} name="square outline" />} content="unaffected inidividual with unknown sex" size="small" />,
  UU: <Popup trigger={<Icon style={iconStyle} name="help" />} content="sex and affected status are unknown" size="small" />,
}

const PedigreeIcon = props =>
  ICON_LOOKUP[`${props.sex}${props.affected}`] ||
  <Popup
    trigger={<Icon style={iconStyle} name="warning sign" />}
    content={<div>ERROR: Unexpected value for affected status {`("${props.affected}")`} or sex {`("${props.sex}")`} </div>}
    size="small"
  />


PedigreeIcon.propTypes = {
  sex: PropTypes.string.isRequired,
  affected: PropTypes.string.isRequired,
}

export default PedigreeIcon
