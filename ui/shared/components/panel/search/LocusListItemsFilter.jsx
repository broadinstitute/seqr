import PropTypes from 'prop-types'
import React, { useCallback } from 'react'
import { Icon, Popup } from 'semantic-ui-react'
import { BaseSemanticInput } from 'shared/components/form/Inputs'
import { ColoredIcon } from 'shared/components/StyledComponents'
import { PANEL_APP_CONFIDENCE_DESCRIPTION, PANEL_APP_CONFIDENCE_LEVEL_COLORS } from 'shared/utils/constants'
import { camelcaseToTitlecase } from 'shared/utils/stringUtils'

const PA_LABEL_HELP = 'A list of genes, can be separated by commas or whitespace.'
const PA_ICON_PROPS = {
  green: {
    name: 'circle',
    title: PANEL_APP_CONFIDENCE_DESCRIPTION[3],
    color: PANEL_APP_CONFIDENCE_LEVEL_COLORS[3],
  },
  amber: {
    name: 'circle',
    title: PANEL_APP_CONFIDENCE_DESCRIPTION[2],
    color: PANEL_APP_CONFIDENCE_LEVEL_COLORS[2],
  },
  red: {
    name: 'circle',
    title: PANEL_APP_CONFIDENCE_DESCRIPTION[1],
    color: PANEL_APP_CONFIDENCE_LEVEL_COLORS[1],
  },
}

const PanelAppItemsFilter = ({ color, value, onChange, ...props }) => {
  const onChangeInner = useCallback((colorVal) => {
    onChange({ ...value, [color]: colorVal })
  })

  const label = `${camelcaseToTitlecase(color)} Genes`
  const iconLabel = (
    <label>
      <ColoredIcon color={color} {...PA_ICON_PROPS[color]} />
      {label}
      &nbsp;
      <Popup trigger={<Icon name="question circle outline" />} content={PA_LABEL_HELP} size="small" position="top center" />
    </label>
  )

  return (
    <BaseSemanticInput
      {...props}
      inputType="TextArea"
      width={3}
      label={iconLabel}
      labelHelp={PA_LABEL_HELP}
      value={value[color]}
      onChange={onChangeInner}
    />
  )
}

PanelAppItemsFilter.propTypes = {
  color: PropTypes.string,
  value: PropTypes.object,
  onChange: PropTypes.func,
}

export const LocusListItemsFilter = ({ ...props }) => {
  const { value } = props

  return value && typeof value === 'object' ?
    [
      <PanelAppItemsFilter {...props} key="green" color="green" name="rawItems.green" />,
      <PanelAppItemsFilter {...props} key="amber" color="amber" name="rawItems.amber" />,
      <PanelAppItemsFilter {...props} key="red" color="red" name="rawItems.red" />,
    ] :
    (
      <BaseSemanticInput {...props} inputType="TextArea" />
    )
}

LocusListItemsFilter.propTypes = {
  value: PropTypes.object,
  onChange: PropTypes.func,
}

export default (LocusListItemsFilter)
