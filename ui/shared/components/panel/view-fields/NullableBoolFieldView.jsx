import React from 'react'
import PropTypes from 'prop-types'
import { Label } from 'semantic-ui-react'

import BaseFieldView from './BaseFieldView'
import { ButtonRadioGroup } from '../../form/Inputs'

const BLOCK_DISPLAY_STYLE = { display: 'block' }

const OPTIONS = [
  { value: true, text: 'Yes', color: 'green' },
  { value: false, text: 'No', color: 'red' },
  { value: null, text: 'Unknown' },
]

export const getNullableBoolField = ({ field, label }) => {
  const options = [...OPTIONS]
  if (label) {
    options.splice(2, 1, { ...OPTIONS[2], label })
  }
  return {
    name: field,
    component: ButtonRadioGroup,
    options,
    format: val => (val === false ? val : (val || null)),
  }
}

const nullableBoolDisplay = (value) => {
  if (value === true) {
    return <Label horizontal basic size="small" content="Yes" color="green" />
  } else if (value === false) {
    return <Label horizontal basic size="small" content="No" color="red" />
  }
  return 'Unknown'
}

const NullableBoolFieldView = React.memo((props) => {
  const fields = [getNullableBoolField(props)]
  return <BaseFieldView
    fieldDisplay={nullableBoolDisplay}
    formFields={fields}
    style={BLOCK_DISPLAY_STYLE}
    showEmptyValues
    compact
    {...props}
  />
})

NullableBoolFieldView.propTypes = {
  field: PropTypes.string.isRequired,
}

export default NullableBoolFieldView
