import React from 'react'
import { Field } from 'redux-form'
import { Form } from 'semantic-ui-react'

const VariantSearchForm = () =>
  <div>
    <Form.Group widths="equal">
      <Field component={Form.Input} name="searchMode" label="Search Mode" />
      <Field component={Form.Input} name="inheritance" label="Inheritance" />
      <Field component={Form.Input} name="qualityFilter.min_ab" label="Min AB" />
    </Form.Group>
  </div>

export default VariantSearchForm
