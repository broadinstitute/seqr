import PropTypes from 'prop-types'
import React from 'react'
import { LOCUS_LIST_ITEMS_FIELD, PANEL_APP_CONFIDENCE_DESCRIPTION, PANEL_APP_CONFIDENCE_LEVEL_COLORS } from 'shared/utils/constants'
import { configuredField } from 'shared/components/form/ReduxFormWrapper'
import { toUniqueCsvString } from 'shared/utils/stringUtils'
import { Form } from 'semantic-ui-react'
import { ColoredIcon } from 'shared/components/StyledComponents'

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

const {
  additionalFormFields,
  fieldDisplay,
  isEditable,
  validate,
  ...LOCUS_LIST_ITEMS_BASE_FIELD
} = { ...LOCUS_LIST_ITEMS_FIELD }
const LOCUS_LIST_RAW_ITEMS_FIELD = { ...LOCUS_LIST_ITEMS_BASE_FIELD, name: 'rawItems', rows: 8, width: 16 }

const PanelAppItemsFilter = ({ color, value, name, onChange }) => {
  const onChangeInner = (event, colorVal) => {
    let result = { ...value, [color]: colorVal }
    result = {
      ...result,
      rawItems: toUniqueCsvString([result.green, result.amber, result.red]),
    }

    onChange(result)
  }

  const label = `${color} genes`
  const iconLabel = (
    <span>
      <ColoredIcon color={color} {...PA_ICON_PROPS[color]} />
      {label}
    </span>
  )

  const result = {
    name,
    label: iconLabel,
    labelHelp: PA_LABEL_HELP,
    fieldDisplay: () => null,
    isEditable: true,
    component: Form.TextArea,
    width: 5,
    rows: 8,
    onChange: onChangeInner,
  }

  return configuredField(result)
}

export const LocusListItemsFilter = ({ ...props }) => {
  const { value } = props

  return value && typeof value === 'object' ?
    [
      <PanelAppItemsFilter {...props} key="green" color="green" name="rawItemsGreen" />,
      <PanelAppItemsFilter {...props} key="amber" color="amber" name="rawItemsAmber" />,
      <PanelAppItemsFilter {...props} key="red" color="red" name="rawItemsRed" />,
    ] :
    (
      configuredField(LOCUS_LIST_RAW_ITEMS_FIELD)
    )
}

LocusListItemsFilter.propTypes = {
  value: PropTypes.object,
  onChange: PropTypes.func,
}

export default (LocusListItemsFilter)
