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

export const NoHoverFamilyLink = React.memo(({ family, path, target, ...props }) => (
  <ColoredLink
    to={`/project/${family.projectGuid}/${path || `family_page/${family.familyGuid}`}`}
    color={FAMILY_ANALYSIS_STATUS_LOOKUP[family[FAMILY_FIELD_ANALYSIS_STATUS]].color}
    target={target}
    {...props} // passing through props allows refs to work for popup trigger
  >
    {family.displayName}
  </ColoredLink>
))

NoHoverFamilyLink.propTypes = {
  family: PropTypes.object.isRequired,
  path: PropTypes.string,
  target: PropTypes.string,
}

const FamilyLink = React.memo(({ family, path, target, disableEdit, PopupClass = Popup }) => React.createElement(
  PopupClass, {
    hoverable: true,
    wide: 'very',
    position: 'right center',
    trigger: <NoHoverFamilyLink family={family} path={path} target={target} />,
    content: (
      <Family
        family={family}
        fields={FAMILY_FIELDS}
        disableEdit={disableEdit}
        disableInternalEdit
        useFullWidth
        disablePedigreeZoom
      />
    ),
  },
))

FamilyLink.propTypes = {
  family: PropTypes.object.isRequired,
  disableEdit: PropTypes.bool,
  path: PropTypes.string,
  target: PropTypes.string,
  PopupClass: PropTypes.elementType,
}

export default FamilyLink
