import React from 'react'
import PropTypes from 'prop-types'
import { NavLink } from 'react-router-dom'
import { Popup } from 'semantic-ui-react'

import {
  FAMILY_FIELD_ANALYSIS_STATUS,
  FAMILY_ANALYSIS_STATUS_LOOKUP,
} from 'shared/utils/constants'
import { ButtonLink } from '../StyledComponents'
import Family from '../panel/family'

const FAMILY_POPUP_STYLE = { maxWidth: '1200px' }


const FamilyLink = ({ family, fields, PopupClass = Popup }) =>
  React.createElement(PopupClass, {
    hoverable: true,
    style: FAMILY_POPUP_STYLE,
    position: 'right center',
    keepInViewPort: true,
    trigger: (
      <ButtonLink
        as={NavLink}
        to={`/project/${family.projectGuid}/family_page/${family.familyGuid}`}
        color={FAMILY_ANALYSIS_STATUS_LOOKUP[family[FAMILY_FIELD_ANALYSIS_STATUS]].color}
        content={family.displayName}
      />
    ),
    content: <Family family={family} fields={fields} useFullWidth disablePedigreeZoom />,
  })

FamilyLink.propTypes = {
  family: PropTypes.object,
  fields: PropTypes.array,
  PopupClass: PropTypes.node,
}

export default FamilyLink
