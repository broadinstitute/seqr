import PropTypes from 'prop-types'
import React, { createElement } from 'react'
import { FormSpy } from 'react-final-form'

import { BaseSemanticInput } from 'shared/components/form/Inputs'
import { ColoredIcon } from 'shared/components/StyledComponents'
import { PANEL_APP_CONFIDENCE_LEVELS, PANEL_APP_CONFIDENCE_DESCRIPTION, PANEL_APP_CONFIDENCE_LEVEL_COLORS } from 'shared/utils/constants'

const PA_ICON_PROPS = Object.entries(PANEL_APP_CONFIDENCE_LEVELS).reduce((acc, [confidence, colorKey]) => {
  const color = PANEL_APP_CONFIDENCE_LEVEL_COLORS[confidence]
  return color ?
    { ...acc, [colorKey]: { name: 'circle', color, title: PANEL_APP_CONFIDENCE_DESCRIPTION[confidence] } } : acc
}, {})

const SUBSCRIPTION = { values: true }

const LocusListItemsFilter = ({ shouldShow, shouldDisable, iconColor, label, filterComponent, ...props }) => (
  <FormSpy subscription={SUBSCRIPTION}>
    {({ values }) => (!shouldShow || shouldShow(values?.search?.locus || {})) && createElement(
      filterComponent || BaseSemanticInput, {
        locus: values?.search?.locus,
        inputType: 'TextArea',
        inline: true,
        rows: 8,
        label: (
          PA_ICON_PROPS[iconColor] ? (
            <label>
              <ColoredIcon {...PA_ICON_PROPS[iconColor]} />
              {label}
            </label>
          ) : label
        ),
        disabled: shouldDisable(values?.search?.locus || {}),
        ...props,
      },
    )}
  </FormSpy>
)

LocusListItemsFilter.propTypes = {
  label: PropTypes.node,
  iconColor: PropTypes.string,
  shouldDisable: PropTypes.func.isRequired,
  shouldShow: PropTypes.func,
  filterComponent: PropTypes.elementType,
}

export default LocusListItemsFilter
