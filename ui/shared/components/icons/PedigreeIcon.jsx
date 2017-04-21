import React from 'react'
import { Icon } from 'semantic-ui-react'

const PedigreeIcon = props =>
  <Icon style={{ fontSize: '13px !important' }} name={
    `${
      (
        ((props.sex === 'U' || props.affected === 'U') ? 'help' : '') +
        ((props.sex === 'M' && props.affected === 'A') ? 'square' : '') +
        ((props.sex === 'F' && props.affected === 'A') ? 'circle' : '') +
        ((props.sex === 'M' && props.affected === 'N') ? 'square outline' : '') +
        ((props.sex === 'F' && props.affected === 'N') ? 'circle thin' : '')
      ) || 'warning sign'
    }`}
  />


PedigreeIcon.propTypes = {
  sex: React.PropTypes.string.isRequired,
  affected: React.PropTypes.string.isRequired,
}

export default PedigreeIcon
