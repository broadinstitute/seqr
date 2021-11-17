import React from 'react'
import PropTypes from 'prop-types'
import { Popup } from 'semantic-ui-react'

import {
  FAMILY_FIELD_DESCRIPTION,
  FAMILY_FIELD_ANALYSIS_STATUS,
  FAMILY_FIELD_ANALYSIS_NOTES,
  FAMILY_FIELD_CASE_NOTES,
  FAMILY_FIELD_INTERNAL_NOTES,
  FAMILY_FIELD_INTERNAL_SUMMARY,
  FAMILY_ANALYSIS_STATUS_LOOKUP,
} from 'shared/utils/constants'
import { ColoredLink } from '../StyledComponents'
import Family from '../panel/family/Family'

const FAMILY_FIELDS = [
  { id: FAMILY_FIELD_DESCRIPTION },
  { id: FAMILY_FIELD_ANALYSIS_STATUS },
  { id: FAMILY_FIELD_CASE_NOTES },
  { id: FAMILY_FIELD_ANALYSIS_NOTES },
  { id: FAMILY_FIELD_INTERNAL_NOTES },
  { id: FAMILY_FIELD_INTERNAL_SUMMARY },
]

const FamilyLink = React.memo(({ family, path, target, disableEdit, PopupClass = Popup }) =>
  React.createElement(PopupClass, {
    hoverable: true,
    wide: 'very',
    position: 'right center',
    trigger: (
      <ColoredLink
        to={`/project/${family.projectGuid}/${path || `family_page/${family.familyGuid}`}`}
        color={FAMILY_ANALYSIS_STATUS_LOOKUP[family[FAMILY_FIELD_ANALYSIS_STATUS]].color}
        target={target}
      >
        {family.displayName}
      </ColoredLink>
    ),
    content: <Family family={family} fields={FAMILY_FIELDS} disableEdit={disableEdit} disableInternalEdit useFullWidth disablePedigreeZoom />,
  }),
)

FamilyLink.propTypes = {
  family: PropTypes.object,
  disableEdit: PropTypes.bool,
  path: PropTypes.string,
  target: PropTypes.string,
  PopupClass: PropTypes.elementType,
}

export default FamilyLink
