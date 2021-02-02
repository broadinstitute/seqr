import React from 'react'
import PropTypes from 'prop-types'
import { Popup } from 'semantic-ui-react'

import {
  FAMILY_FIELD_DESCRIPTION,
  FAMILY_FIELD_ANALYSIS_STATUS,
  FAMILY_FIELD_ANALYSIS_NOTES,
  FAMILY_FIELD_ANALYSIS_SUMMARY,
  FAMILY_FIELD_INTERNAL_NOTES,
  FAMILY_FIELD_INTERNAL_SUMMARY,
  FAMILY_ANALYSIS_STATUS_LOOKUP,
} from 'shared/utils/constants'
import { ColoredLink } from '../StyledComponents'
import Family from '../panel/family'

const FAMILY_FIELDS = [
  { id: FAMILY_FIELD_DESCRIPTION, canEdit: true },
  { id: FAMILY_FIELD_ANALYSIS_STATUS, canEdit: true },
  { id: FAMILY_FIELD_ANALYSIS_NOTES, canEdit: true },
  { id: FAMILY_FIELD_ANALYSIS_SUMMARY, canEdit: true },
  { id: FAMILY_FIELD_INTERNAL_NOTES },
  { id: FAMILY_FIELD_INTERNAL_SUMMARY },
]

const FamilyLink = React.memo(({ family, fields, path, target, disableEdit, PopupClass = Popup }) =>
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
    content: <Family family={family} fields={fields || FAMILY_FIELDS} disableEdit={disableEdit} useFullWidth disablePedigreeZoom />,
  }),
)

FamilyLink.propTypes = {
  family: PropTypes.object,
  fields: PropTypes.array,
  disableEdit: PropTypes.bool,
  path: PropTypes.string,
  target: PropTypes.string,
  PopupClass: PropTypes.elementType,
}

export default FamilyLink
