import React, { createElement } from 'react'
import PropTypes from 'prop-types'

import { helpLabel, StyledForm } from './ReduxFormWrapper'

const StateChangeForm = React.memo(({ fields, initialValues, updateField }) =>
  <StyledForm inline hasSubmitButton={false}>
    {fields.map(({ component, name, label, labelHelp, ...fieldProps }) =>
      createElement(component, {
        key: name,
        value: initialValues[name],
        label: helpLabel(label, labelHelp),
        onChange: updateField(name),
        ...fieldProps,
      }),
    )}
  </StyledForm>,

)

StateChangeForm.propTypes = {
  initialValues: PropTypes.object,
  updateField: PropTypes.func,
  fields: PropTypes.array.isRequired,
}

export default StateChangeForm
