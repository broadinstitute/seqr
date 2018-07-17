import React from 'react'
import PropTypes from 'prop-types'
import { Form, Icon } from 'semantic-ui-react'

import ButtonLink from '../buttons/ButtonLink'
import { Select } from './Inputs'
import { configuredFields } from './ReduxFormWrapper'

const GENOME_VERSION_OPTIONS = [{ value: '37' }, { value: '38' }]

const FIELDS = [
  { fieldName: 'chrom', label: 'Chrom', maxLength: 2 },
  { fieldName: 'start', label: 'Start', type: 'number' },
  { fieldName: 'end', label: 'End', type: 'number' },
  { fieldName: 'genomeVersion', label: 'Genome Version', component: Select, options: GENOME_VERSION_OPTIONS },
]

const IntervalField = ({ name, error, removeField }) => {
  const fields = {
    fields: FIELDS.map(({ fieldName, ...field }) => ({ name: `${name}.${fieldName}`, width: 4, error, ...field })),
  }
  return (
    <Form.Group inline>
      <ButtonLink onClick={removeField}><Icon link name="trash" /></ButtonLink>
      {configuredFields(fields)}
    </Form.Group>
  )
}

IntervalField.propTypes = {
  name: PropTypes.string,
  error: PropTypes.bool,
  removeField: PropTypes.func,
}

export default IntervalField
