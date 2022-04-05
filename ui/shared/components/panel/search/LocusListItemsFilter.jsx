import PropTypes from 'prop-types'
import React, { useCallback } from 'react'
import { Icon, Popup } from 'semantic-ui-react'
import { BaseSemanticInput } from 'shared/components/form/Inputs'
import { ColoredIcon } from 'shared/components/StyledComponents'
import { PANEL_APP_CONFIDENCE_DESCRIPTION, PANEL_APP_CONFIDENCE_LEVEL_COLORS } from 'shared/utils/constants'
import { camelcaseToTitlecase } from 'shared/utils/stringUtils'

const PA_POPUP_HELP = (
  <Popup
    trigger={<Icon name="question circle outline" />}
    content="A list of genes, can be separated by commas or whitespace."
    size="small"
    position="top center"
  />
)
const PA_ICON_PROPS = Object.entries({ 1: 'red', 2: 'amber', 3: 'green' }).reduce((acc, [confidence, color]) => ({
  ...acc,
  [color]: {
    name: 'circle',
    title: PANEL_APP_CONFIDENCE_DESCRIPTION[confidence],
    color: PANEL_APP_CONFIDENCE_LEVEL_COLORS[confidence],
  },
}), {})

const PanelAppItemsFilter = ({ color, value, onChange, ...props }) => {
  const onChangeInner = useCallback((colorVal) => {
    onChange({ ...value, [color]: colorVal })
  })

  const label = `${camelcaseToTitlecase(color)} Genes`
  const iconLabel = color === 'none' ?
    (
      <label>
        Genes
        &nbsp;
        {PA_POPUP_HELP}
      </label>
    ) :
    (
      <label>
        <ColoredIcon {...PA_ICON_PROPS[color]} />
        {label}
        &nbsp;
        {PA_POPUP_HELP}
      </label>
    )

  return (
    <BaseSemanticInput
      {...props}
      inputType="TextArea"
      width={3}
      label={iconLabel}
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
      <PanelAppItemsFilter {...props} key="none" color="none" name="rawItems.none" />,
    ] :
    (
      <BaseSemanticInput {...props} inputType="TextArea" />
    )
}

LocusListItemsFilter.propTypes = {
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.object]),
  onChange: PropTypes.func,
}

export default (LocusListItemsFilter)
