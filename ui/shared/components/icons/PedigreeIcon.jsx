import React from 'react'
import PropTypes from 'prop-types'

import { Icon, Popup } from 'semantic-ui-react'

import { SEX_LOOKUP, AFFECTED_LOOKUP } from 'shared/utils/constants'

const ICON_LOOKUP = {

  MA: { icon: 'square' },
  MN: { icon: 'square outline' },
  MU: {
    iconGroup: (
      <Icon.Group>
        <Icon name="square outline" />
        <Icon size="small" name="question" />
      </Icon.Group>
    ),
  },

  FA: { icon: 'circle' },
  FN: { icon: 'circle outline' },
  FU: { icon: 'question circle outline' },

  UA: { icon: 'clone' },
  UN: { icon: 'clone outline' },
  UU: { icon: 'question' },
}

const PedigreeIcon = React.memo((props) => {
  const iconProps = ICON_LOOKUP[`${props.sex}${props.affected}`]
  return (
    <Popup
      trigger={iconProps.iconGroup || (
        <span>
          <Icon name={iconProps.icon || 'warning sign'} />
          {props.label}
        </span>
      )}
      content={
        <div>
          <b>Sex: &nbsp;</b>
          {SEX_LOOKUP[props.sex] || 'INVALID'}
          <br />
          <b>Status: &nbsp;</b>
          {AFFECTED_LOOKUP[props.affected] || 'INVALID'}
          {props.popupContent}
        </div>
      }
      header={props.popupHeader}
      size="small"
      wide="very"
      position="top center"
      hoverable
    />
  )
})

PedigreeIcon.propTypes = {
  sex: PropTypes.string.isRequired,
  affected: PropTypes.string.isRequired,
  popupHeader: PropTypes.string,
  popupContent: PropTypes.node,
  label: PropTypes.node,
}

export default PedigreeIcon
