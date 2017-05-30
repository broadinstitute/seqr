import React from 'react'
import PropTypes from 'prop-types'

import { Icon, Popup } from 'semantic-ui-react'

const iconStyle = { fontSize: '13px !important' }

const ICON_LOOKUP = {
  MA: <Icon style={iconStyle} name="square" />,
  MN: <Icon style={iconStyle} name="square outline" />,
  FA: <Icon style={iconStyle} name="circle" />,
  FN: <Icon style={iconStyle} name="circle thin" />,
  UA: <span style={iconStyle}>{'\u25C6'}</span>,
  UN: <span style={iconStyle}>{'\u25C7'}</span>,
  UU: <Popup trigger={<Icon style={iconStyle} name="help" />} content={<div>sex and affected status unknown</div>} size="small" />,
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
