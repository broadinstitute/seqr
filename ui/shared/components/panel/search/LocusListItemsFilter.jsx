import PropTypes from 'prop-types'
import React from 'react'
import { LOCUS_LIST_ITEMS_FIELD, PANEL_APP_CONFIDENCE_DESCRIPTION, PANEL_APP_CONFIDENCE_LEVEL_COLORS } from 'shared/utils/constants'
import { configuredField } from 'shared/components/form/ReduxFormWrapper'
import { toUniqueCsvString } from 'shared/utils/stringUtils'
import { Form } from 'semantic-ui-react'
import { ColoredIcon } from 'shared/components/StyledComponents'

const PA_LABEL_HELP = 'A list of genes, can be separated by commas or whitespace.'
const PA_GREEN_ICON = (
  <ColoredIcon
    name="circle"
    title={PANEL_APP_CONFIDENCE_DESCRIPTION[3]}
    color={PANEL_APP_CONFIDENCE_LEVEL_COLORS[3]}
  />
)
const PA_AMBER_ICON = (
  <ColoredIcon
    name="circle"
    title={PANEL_APP_CONFIDENCE_DESCRIPTION[2]}
    color={PANEL_APP_CONFIDENCE_LEVEL_COLORS[2]}
  />
)
const PA_RED_ICON = (
  <ColoredIcon
    name="circle"
    title={PANEL_APP_CONFIDENCE_DESCRIPTION[1]}
    color={PANEL_APP_CONFIDENCE_LEVEL_COLORS[1]}
  />
)

const {
  additionalFormFields,
  fieldDisplay,
  isEditable,
  validate,
  ...LOCUS_LIST_ITEMS_BASE_FIELD
} = { ...LOCUS_LIST_ITEMS_FIELD }
const LOCUS_LIST_RAW_ITEMS_FIELD = { ...LOCUS_LIST_ITEMS_BASE_FIELD, name: 'rawItems', rows: 8, width: 16 }
const LOCUS_LIST_GREEN_ITEMS_FIELD = { ...LOCUS_LIST_ITEMS_BASE_FIELD, name: 'rawItemsGreen', label: 'Green Genes', labelHelp: PA_LABEL_HELP, labelIcon: PA_GREEN_ICON, rows: 8, width: 5 }
const LOCUS_LIST_AMBER_ITEMS_FIELD = { ...LOCUS_LIST_ITEMS_BASE_FIELD, name: 'rawItemsAmber', label: 'Amber Genes', labelHelp: PA_LABEL_HELP, labelIcon: PA_AMBER_ICON, rows: 8, width: 5 }
const LOCUS_LIST_RED_ITEMS_FIELD = { ...LOCUS_LIST_ITEMS_BASE_FIELD, name: 'rawItemsRed', label: 'Red Genes', labelHelp: PA_LABEL_HELP, labelIcon: PA_RED_ICON, rows: 8, width: 5 }

export const LocusListItemsFilter = ({ value, onChange }) => {
  const handleChange = (currFilterValue, filterField) => (_, newValue) => {
    let result = { ...currFilterValue, [filterField]: newValue }
    if (currFilterValue.isPanelAppList) {
      result = {
        ...result,
        rawItems: toUniqueCsvString([result.rawItemsGreen, result.rawItemsAmber, result.rawItemsRed]),
      }
    }

    onChange(result)
  }

  const RAW_FIELD = { ...LOCUS_LIST_RAW_ITEMS_FIELD, onChange: handleChange(value, 'rawItems') }
  const GREEN_FIELD = { ...LOCUS_LIST_GREEN_ITEMS_FIELD, onChange: handleChange(value, 'rawItemsGreen') }
  const AMBER_FIELD = { ...LOCUS_LIST_AMBER_ITEMS_FIELD, onChange: handleChange(value, 'rawItemsAmber') }
  const RED_FIELD = { ...LOCUS_LIST_RED_ITEMS_FIELD, onChange: handleChange(value, 'rawItemsRed') }

  return value?.isPanelAppList ?
    (
      <Form.Field>
        <Form.Group>
          {configuredField(GREEN_FIELD)}
          {configuredField(AMBER_FIELD)}
          {configuredField(RED_FIELD)}
        </Form.Group>
      </Form.Field>
    ) :
    (
      <Form.Field>
        <Form.Group>
          {configuredField(RAW_FIELD)}
        </Form.Group>
      </Form.Field>
    )
}

LocusListItemsFilter.propTypes = {
  value: PropTypes.string,
  onChange: PropTypes.func,
}

export default (LocusListItemsFilter)
