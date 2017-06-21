import React from 'react'
import PropTypes from 'prop-types'

import { Icon, Popup } from 'semantic-ui-react'

const iconStyle = { fontSize: '13px !important' }

const ICON_LOOKUP = {
  MA: <Icon style={iconStyle} name="square" />,
  MN: <Icon style={iconStyle} name="square outline" />,
  MU: <Popup trigger={<Icon style={iconStyle} name="question square outline" />} content="male with unknown affected status" size="small" />,

  FA: <Icon style={iconStyle} name="circle" />,
  FN: <Icon style={iconStyle} name="circle thin" />,
  FU: <Popup trigger={<Icon style={iconStyle} name="question circle outline" />} content="female with unknown affected status" size="small" />,

  UA: <Popup trigger={<span style={iconStyle}>{'\u25C6'}</span>} content="affected inidividual with unknown sex" size="small" />,
  UN: <Popup trigger={<span style={iconStyle}>{'\u25C7'}</span>} content="unaffected inidividual with unknown sex" size="small" />,
  UU: <Popup trigger={<Icon style={iconStyle} name="help" />} content="sex and affected status are unknown" size="small" />,
}

const PedigreeIcon = props => ICON_LOOKUP[`${props.sex}${props.affected}`] ||
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
