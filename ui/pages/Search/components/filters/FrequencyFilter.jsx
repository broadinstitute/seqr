import React from 'react'
import PropTypes from 'prop-types'
import { Form } from 'semantic-ui-react'

import { VerticalSpacer } from 'shared/components/Spacers'
import { StepSlider, IntegerInput, Select } from 'shared/components/form/Inputs'

const AF_STEPS = [
  0,
  0.0001,
  0.0005,
  0.001,
  0.005,
  0.01,
  0.02,
  0.03,
  0.04,
  0.05,
  0.1,
  1,
]

const AF_STEP_LABELS = {
  0.0001: '1e-4',
  0.0005: '5e-4',
  0.001: '1e-3',
  0.005: '5e-3',
}

const AF_OPTIONS = AF_STEPS.map(value => ({ value }))

const FrequencyIntegerInput = ({ label, value, field, nullField, inlineAF, onChange }) =>
  <IntegerInput
    label={label}
    value={value[field]}
    min={0}
    max={100}
    width={inlineAF ? 5 : 8}
    onChange={(val) => {
      const updateFields = { [field]: val }
      if (nullField) {
        updateFields[nullField] = null
      }
      onChange({ ...value, ...updateFields })
    }}
  />

FrequencyIntegerInput.propTypes = {
  value: PropTypes.object,
  field: PropTypes.string,
  nullField: PropTypes.string,
  label: PropTypes.string,
  inlineAF: PropTypes.bool,
  onChange: PropTypes.func,
}

const FrequencyFilter = ({ value, onChange, homHemi, inlineAF }) => {
  const afProps = {
    value: value.af,
    onChange: val => onChange({ ...value, af: val, ac: null }),
  }
  return (
    <span>
      {!inlineAF &&
        <div>
          <Form.Field control={StepSlider} steps={AF_STEPS} stepLabels={AF_STEP_LABELS} {...afProps} />
          <VerticalSpacer height={15} />
        </div>
      }
      <Form.Group inline>
        {inlineAF &&
          <Select options={AF_OPTIONS} width={6} label="AF" {...afProps} />
        }
        <FrequencyIntegerInput
          label="AC"
          field="ac"
          nullField="af"
          value={value}
          inlineAF={inlineAF}
          onChange={onChange}
        />
        {homHemi &&
          <FrequencyIntegerInput label="H/H" field="hh" value={value} inlineAF={inlineAF} onChange={onChange} />
        }
      </Form.Group>
    </span>
  )
}

FrequencyFilter.propTypes = {
  value: PropTypes.object,
  onChange: PropTypes.func,
  homHemi: PropTypes.bool,
  inlineAF: PropTypes.bool,
}

export default FrequencyFilter
