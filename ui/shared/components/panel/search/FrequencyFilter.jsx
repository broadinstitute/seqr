import React from 'react'
import PropTypes from 'prop-types'
import { Form } from 'semantic-ui-react'

import { VerticalSpacer } from 'shared/components/Spacers'
import { StepSlider, IntegerInput, Select } from 'shared/components/form/Inputs'
import { FREQUENCIES, THIS_CALLSET_FREQUENCY, SV_CALLSET_FREQUENCY } from './constants'

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

const FrequencyIntegerInput = React.memo(({ label, value, field, nullField, inlineAF, onChange }) =>
  <IntegerInput
    label={label}
    value={(value || {})[field]}
    min={0}
    max={100}
    width={inlineAF ? 3 : 8}
    onChange={(val) => {
      const updateFields = { [field]: val }
      if (nullField) {
        updateFields[nullField] = null
      }
      onChange({ ...value, ...updateFields })
    }}
  />,
)

FrequencyIntegerInput.propTypes = {
  value: PropTypes.object,
  field: PropTypes.string,
  nullField: PropTypes.string,
  label: PropTypes.string,
  inlineAF: PropTypes.bool,
  onChange: PropTypes.func,
}

export const AfFilter = ({ value, onChange, inline, label, width }) => {
  const afProps = {
    value: (value || {}).af,
    onChange: val => onChange({ ...value, af: val, ac: null }),
  }
  return inline ?
    <Select options={AF_OPTIONS} width={width || 5} label={label || 'AF'} {...afProps} /> :
    <Form.Field control={StepSlider} steps={AF_STEPS} stepLabels={AF_STEP_LABELS} {...afProps} />
}

AfFilter.propTypes = {
  value: PropTypes.object,
  onChange: PropTypes.func,
  inline: PropTypes.bool,
  label: PropTypes.string,
  width: PropTypes.number,
}

export const FrequencyFilter = ({ value, onChange, homHemi, inlineAF, children }) => (
  <span>
    {!inlineAF &&
      <div>
        <AfFilter value={value} onChange={onChange} />
        <VerticalSpacer height={15} />
      </div>
    }
    <Form.Group inline>
      {inlineAF &&
        <AfFilter value={value} onChange={onChange} inline />
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
      {children}
    </Form.Group>
  </span>
)

FrequencyFilter.propTypes = {
  value: PropTypes.object,
  onChange: PropTypes.func,
  homHemi: PropTypes.bool,
  inlineAF: PropTypes.bool,
  children: PropTypes.node,
}

const formatHeaderValue = values =>
  Object.values(values).reduce((acc, value) => ({
    af: value.af === acc.af ? value.af : null,
    ac: value.ac === acc.ac ? value.ac : null,
    hh: value.hh === acc.hh ? value.hh : null,
  }), Object.values(values)[0])

export const HeaderFrequencyFilter = ({ value, onChange, ...props }) => {
  const { callset, sv_callset: svCallset, ...freqValues } = value || {}
  const headerValue = freqValues ? formatHeaderValue(freqValues) : {}

  const onCallsetChange = val =>
    onChange({ ...freqValues, [THIS_CALLSET_FREQUENCY]: val, [SV_CALLSET_FREQUENCY]: val })

  const onFreqChange = val =>
    onChange(FREQUENCIES.filter(({ name }) => name !== THIS_CALLSET_FREQUENCY && name !== SV_CALLSET_FREQUENCY).reduce(
      (acc, { name }) => ({ ...acc, [name]: val }), value || {}))

  return (
    <FrequencyFilter {...props} value={headerValue} onChange={onFreqChange} homHemi inlineAF>
      <AfFilter value={callset} onChange={onCallsetChange} inline label="Callset AF" />
      <FrequencyIntegerInput
        label="Callset AC"
        field="ac"
        nullField="af"
        value={callset}
        inlineAF
        onChange={onCallsetChange}
      />
    </FrequencyFilter>
  )
}

HeaderFrequencyFilter.propTypes = {
  value: PropTypes.object,
  onChange: PropTypes.func,
}

