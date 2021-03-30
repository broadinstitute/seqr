/* eslint-disable react/no-multi-comp */

import React, { createElement } from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Form, List, Button, Pagination as PaginationComponent, Search, Icon, Popup } from 'semantic-ui-react'
import Slider from 'react-rangeslider'
import { JsonEditor } from 'jsoneditor-react'
import 'react-rangeslider/lib/index.css'

import { helpLabel } from './ReduxFormWrapper'
import { VerticalSpacer } from '../Spacers'

export class BaseSemanticInput extends React.Component {

  static propTypes = {
    inputStyle: PropTypes.any,
    onChange: PropTypes.func,
    inputType: PropTypes.string.isRequired,
    options: PropTypes.array,
  }

  handleChange = (e, data) => {
    this.props.onChange(data.value === undefined ? data : data.value)
  }

  render() {
    const { inputStyle, inputType, ...props } = this.props
    return createElement(Form[inputType], { ...props, onChange: this.handleChange, onBlur: null, style: inputStyle !== undefined ? inputStyle : null })
  }

  shouldComponentUpdate(nextProps, nextState) {
    if (nextProps.options) {
      if (nextProps.options.length !== (this.props.options || []).length) {
        return true
      }
      Object.entries(nextProps.options).forEach(([i, opt]) => { //eslint-disable-line consistent-return
        if (['value', 'text', 'color', 'disabled', 'description'].some(k => opt[k] !== this.props.options[i][k])) {
          return true
        }
      })
    }
    if (Object.keys(nextProps).filter(k => k !== 'onChange' && k !== 'options').some(k => nextProps[k] !== this.props[k])) {
      return true
    }
    return nextState !== this.state
  }
}


export const IntegerInput = React.memo(({ onChange, min, max, value, ...props }) =>
  <BaseSemanticInput
    {...props}
    value={Number.isInteger(value) ? value : ''}
    inputType="Input"
    type="number"
    min={min}
    max={max}
    onChange={(stringVal) => {
      if (stringVal === '') {
        onChange(null)
      }
      const val = parseInt(stringVal, 10)
      if ((min === undefined || val >= min) && (max === undefined || val <= max)) {
        onChange(val)
      }
    }}
  />,
)

IntegerInput.propTypes = {
  onChange: PropTypes.func,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  min: PropTypes.number,
  max: PropTypes.number,
}


const labelStyle = (color) => { return color ? { color: 'white', backgroundColor: color } : {} }

const styledOption = (option) => {
  return {
    value: option.value,
    key: option.key || option.text || option.value,
    text: option.text || option.name || option.value,
    label: option.color ? { empty: true, circular: true, style: labelStyle(option.color) } : null,
    color: option.color,
    disabled: option.disabled,
    description: option.description,
  }
}

const processOptions = (options, includeCategories) => {
  let currCategory = null
  return options.reduce((acc, option) => {
    if (includeCategories && option.category !== currCategory) {
      currCategory = option.category
      if (option.category) {
        acc.push({ text: option.category, disabled: true })
      }
    }
    acc.push(option)
    return acc
  }, []).map(styledOption)
}

export const Dropdown = React.memo(({ options, includeCategories, ...props }) =>
  <BaseSemanticInput
    {...props}
    inputType="Dropdown"
    options={processOptions(options, includeCategories)}
    noResultsMessage={null}
    tabIndex="0"
  />,
)


Dropdown.propTypes = {
  options: PropTypes.array,
  includeCategories: PropTypes.bool,
}

export const filteredPredictions = {}

const updateFilterPredictionValue = (prediction, value) => {
  if (!(prediction in filteredPredictions)) {
    filteredPredictions[prediction] = { value, ...filteredPredictions[prediction] }
  } else {
    filteredPredictions[prediction].value = value
  }
}

const updateFilterPredictionOperator = (prediction, operator) => {
  if (!(prediction in filteredPredictions)) {
    filteredPredictions[prediction] = { operator, ...filteredPredictions[prediction] }
  } else {
    filteredPredictions[prediction].operator = operator
  }
}

export const InputGroup = React.memo((props) => {
  const { inputGroupId, isDefaultGroup, options, handleOptionDelete, handleOptionValueUpdate, handleOptionOperatorUpdate, compareOptions } = props
  const inputGroupStyle = {
    padding: '10px',
  }

  const dropdownGroupStyle = {
    paddingTop: '35px',
  }

  const iconStyle = {
    zIndex: '2',
    position: 'absolute',
    right: '0',
    top: '0',
  }

  return (
    <div key={`inputGroup-${inputGroupId}`}>
      {options.map(option =>
        <div style={{ float: 'left', width: '33%' }} key={option.label}>
          <div style={{ gridTemplateColumns: '20% 80%', gridGap: '5px', display: 'grid' }}>
            <BaseSemanticInput
              inputType="Dropdown"
              inputStyle={dropdownGroupStyle}
              options={compareOptions}
              noResultsMessage={null}
              value={!isDefaultGroup ? option.operator : undefined}
              tabIndex="0"
              onClick={() => { }}
              onFocus={() => { }}
              onChange={(operator) => {
                updateFilterPredictionOperator(option.name, operator)
                if (!isDefaultGroup) {
                  handleOptionOperatorUpdate(option, operator)
                }
              }}
            />
            <div>
              {/* eslint-disable-next-line jsx-a11y/label-has-for */}
              <label style={{ fontWeight: 'bold', whiteSpace: 'noWrap' }}>{helpLabel(option.label, option.labelHelp)}</label>
              <div style={{ position: 'relative' }}>
                <BaseSemanticInput
                  id={option.name}
                  inputType="Input"
                  inputStyle={inputGroupStyle}
                  key={option.name}
                  value={!isDefaultGroup ? option.value : undefined}
                  onChange={(value) => {
                    updateFilterPredictionValue(option.name, value)
                    if (!isDefaultGroup) {
                      handleOptionValueUpdate(option.name)
                    }
                  }}
                  onFocus={() => { }}
                />
                {(option.isDefault !== undefined || false) &&
                  <Icon name="times circle outline" style={iconStyle}
                    onClick={() => {
                      handleOptionDelete(option.name)
                    }}
                  />
                }
              </div>
            </div>
          </div>
        </div>,
      )}
    </div>
  )
})

InputGroup.propTypes = {
  options: PropTypes.array,
  inputGroupId: PropTypes.string,
  compareOptions: PropTypes.array,
  handleOptionDelete: PropTypes.func,
  handleOptionValueUpdate: PropTypes.func,
  handleOptionOperatorUpdate: PropTypes.func,
  isDefaultGroup: PropTypes.bool,
}

export const GridInputGroup = React.memo((props) => {
  const { options, gridGroupName, isDefaultGroup, compareOptions, topSpacing, handleOptionDelete, handleOptionValueUpdate, handleOptionOperatorUpdate, ...baseProps } = props
  const inputOptions = options[0] !== undefined ? options[0].options : []
  const optionChunks = []
  const optionChunkCount = 5
  const inputOptionsCopy = [...inputOptions]
  for (let i = optionChunkCount; i > 0; i--) {
    const optionChunk = inputOptionsCopy.splice(0, Math.ceil(inputOptionsCopy.length / i))
    optionChunks.push({ id: `${gridGroupName}-${i}`, key: `${gridGroupName}-chunk${i}`, chunk: optionChunk })
  }
  const floatStyle = {
    clear: 'both',
  }
  return (
    <div>
      {(inputOptions.length > 0 && topSpacing === true) &&
        <VerticalSpacer height={30} />
      }
      {optionChunks.map((chunk) => {
        return <InputGroup inputGroupId={chunk.id} key={chunk.key} options={chunk.chunk} isDefaultGroup={isDefaultGroup} handleOptionDelete={handleOptionDelete} handleOptionValueUpdate={handleOptionValueUpdate} handleOptionOperatorUpdate={handleOptionOperatorUpdate} compareOptions={compareOptions} {...baseProps} />
      })}
      <div style={floatStyle} />
      <VerticalSpacer height={40} />
    </div>
  )
})

GridInputGroup.propTypes = {
  options: PropTypes.array,
  gridGroupName: PropTypes.string,
  topSpacing: PropTypes.bool,
  handleOptionDelete: PropTypes.func,
  compareOptions: PropTypes.array,
  handleOptionValueUpdate: PropTypes.func,
  handleOptionOperatorUpdate: PropTypes.func,
  isDefaultGroup: PropTypes.bool,
}

let searchOptions = []
const getElasticSearchIndicies = async () => {
  // Clear searchOptions and get new data
  searchOptions = []

  const url = 'localhost:9200'

  // Get all keys from Elasticsearch
  let response = await fetch(`${url}/_mapping`)
  let data = await response.json()

  // Include only index names that are not from ElasticSearch (the ones that start with dot)
  const indexNames = Object.keys(data).filter(key => key[0] !== '.')

  // For each index name get properties
  /* eslint-disable no-await-in-loop */
  for (let indexNameIdx = 0; indexNameIdx < indexNames.length; indexNameIdx++) {
    const indexName = indexNames[indexNameIdx]
    response = await fetch(`${url}/${indexName}`)
    data = await response.json()

    /* eslint-disable no-loop-func */
    Object.keys(data[indexName].mappings.properties).forEach((property) => {
      searchOptions.push({ title: property })
    })
  }
}

export const InlineInputGroup = React.memo((props) => {
  const { options, compareOptions, searchHelpText, ...baseProps } = props

  getElasticSearchIndicies()

  return (
    <div>
      <VerticalSpacer height={50} />
      <GridInputGroup
        {...baseProps}
        options={options}
        gridGroupName="baseAnnotationsGridGroup"
        isDefaultGroup
        compareOptions={compareOptions}
        handleOptionDelete={() => { }}
        handleOptionValueUpdate={() => { }}
        handleOptionOperatorUpdate={() => { }}
      />
      <VerticalSpacer height={50} />
      <SearchAnnotations
        {...baseProps}
        onChange={() => { }}
        searchOptions={searchOptions}
        onResultSelect={() => { }}
        compareOptions={compareOptions}
        searchHelpText={searchHelpText}
        gridGroupName="customAnnotationsGridGroup"
      />
    </div>
  )
})

InlineInputGroup.propTypes = {
  options: PropTypes.array,
  compareOptions: PropTypes.array,
  searchHelpText: PropTypes.string,
}

export const Select = props =>
  <Dropdown selection fluid {...props} />


Select.propTypes = {
  options: PropTypes.array,
}

export class SearchAnnotations extends React.PureComponent {
  static propTypes = {
    onChange: PropTypes.func,
    searchOptions: PropTypes.array,
    onResultSelect: PropTypes.func,
    compareOptions: PropTypes.array,
    searchHelpText: PropTypes.string,
    gridGroupName: PropTypes.string,
  }

  state = {
    searchResults: this.props.searchOptions,
    options: [{ options: [] }],
    compareOptions: this.props.compareOptions,
  }

  handleResultSelect = (e, { result }) => {
    this.props.onResultSelect(e, result.title)
    this.setState((prevState) => {
      const previousOptions = prevState.options[0].options
      const newOptions = [...previousOptions]
      const optionResult = newOptions.filter((option) => { return option.name === result.title })
      if (optionResult.length === 0) {
        const hello = {
          name: result.title.toLowerCase(),
          label: result.title,
          isDefault: false,
          value: '',
          operator: '',
        }
        newOptions.push(hello)
      }
      return { options: [{ options: newOptions }] }
    })
  }

  handleOptionOperatorUpdate = (option, operator) => {
    this.setState((prevState) => {
      const inputOptions = prevState.options[0] !== undefined ? prevState.options[0].options : []
      const index = inputOptions.findIndex(opt => opt.name === option.name)
      if (index > -1) {
        inputOptions[index].operator = operator
      }
      return { options: [{ options: inputOptions }] }
    })
  }

  handleOptionValueUpdate = (optionName) => {
    const optionValue = filteredPredictions[optionName].value
    this.setState((prevState) => {
      const inputOptions = prevState.options[0] !== undefined ? prevState.options[0].options : []
      const index = inputOptions.findIndex(opt => opt.name === optionName)
      if (index > -1) {
        inputOptions[index].value = optionValue
      }
      return { options: [{ options: inputOptions }] }
    })
  }

  handleSearchChange = (e, data) => {
    this.setState({
      searchResults: this.props.searchOptions.filter(({ title }) => title.toLowerCase().includes(data.value.toLowerCase())),
    })
    this.props.onChange(e, data)
  }
  handleOptionDelete = (optionName) => {
    this.setState((prevState) => {
      const inputOptions = prevState.options[0] !== undefined ? prevState.options[0].options : []
      const index = inputOptions.findIndex(option => option.name === optionName)
      if (index > -1) {
        inputOptions.splice(index, 1)
      }
      delete filteredPredictions[optionName]
      return { options: [{ options: inputOptions }] }
    })
  }

  render() {
    // eslint-disable-next-line no-shadow
    const { onChange, searchOptions, onResultSelect, compareOptions, searchHelpText, ...props } = this.props
    return (
      <div>
        {/* eslint-disable-next-line jsx-a11y/label-has-for */}
        <label> Search for additional annotations <Popup trigger={<Icon name="question circle outline" />} content={searchHelpText} size="small" position="top center" /></label>
        <CustomAnnotationSearch
          results={this.state.searchResults}
          onResultSelect={this.handleResultSelect}
          onSearchChange={this.handleSearchChange}
        />
        <GridInputGroup
          {...props}
          options={this.state.options}
          compareOptions={this.state.compareOptions}
          gridGroupName={this.props.gridGroupName}
          topSpacing
          handleOptionDelete={this.handleOptionDelete}
          handleOptionValueUpdate={this.handleOptionValueUpdate}
          handleOptionOperatorUpdate={this.handleOptionOperatorUpdate}
        />
      </div>
    )
  }
}

export const CustomAnnotationSearch = styled(Search)`
  .input + .results {
    max-height: 210px;
    overflow-y: scroll;
  }
`

export class Multiselect extends React.PureComponent {
  static propTypes = {
    color: PropTypes.string,
    allowAdditions: PropTypes.bool,
  }

  renderLabel = (data) => {
    return { color: this.props.color, content: data.text || data.value, style: labelStyle(data.color) }
  }

  render() {
    return <AddableSelect
      {...this.props}
      renderLabel={this.renderLabel}
      allowAdditions={this.props.allowAdditions || false}
      multiple
    />
  }
}

export const LargeMultiselect = styled(({ dispatch, ...props }) => <Multiselect {...props} />)`
  .ui.search.dropdown .menu {
    max-height: calc(90vh - 220px);
    
    .item {
      clear: both;
      
      .description {
        max-width: 50%;
        text-align: right;
      }
    }
  }
`

export class AddableSelect extends React.PureComponent {
  static propTypes = {
    options: PropTypes.array,
    allowAdditions: PropTypes.bool,
    addValueOptions: PropTypes.bool,
    value: PropTypes.any,
  }

  constructor(props) {
    super(props)

    let { options } = props
    if (props.addValueOptions && props.value) {
      const valueOptions = props.value.filter(val => !props.options.some(({ value }) => value === val)).map(value => ({ value }))
      options = [...options, ...valueOptions]
    }
    this.state = { options }
  }

  handleAddition = (e, { value }) => {
    this.setState({
      options: [{ value }, ...this.state.options],
    })
  }

  resetOptions = () => {
    this.setState({ options: this.props.options })
  }

  render() {
    const { addValueOptions, ...props } = this.props
    return <Select
      {...props}
      options={this.state.options}
      allowAdditions={this.props.allowAdditions !== false}
      onAddItem={this.handleAddition}
      search
    />
  }

  componentDidUpdate(prevProps) {
    if (this.props.options.length !== prevProps.options.length) {
      this.resetOptions()
    }
  }
}


export class SearchInput extends React.PureComponent {
  static propTypes = {
    onChange: PropTypes.func,
    options: PropTypes.array,
  }

  state = {
    results: this.props.options,
  }

  handleResultSelect = (e, { result }) => this.props.onChange(e, result.title)

  handleSearchChange = (e, data) => {
    this.setState({
      results: this.props.options.filter(({ title }) => title.toLowerCase().includes(data.value.toLowerCase())),
    })
    this.props.onChange(e, data)
  }

  render() {
    const { options, onChange, ...props } = this.props
    return <Search
      {...props}
      results={this.state.results}
      onResultSelect={this.handleResultSelect}
      onSearchChange={this.handleSearchChange}
    />
  }
}

const YEAR_OPTIONS = [...Array(130).keys()].map(i => ({ value: i + 1900 }))
const YEAR_OPTIONS_UNKNOWN = [{ value: 0, text: 'Unknown' }, ...YEAR_OPTIONS]
const YEAR_OPTIONS_ALIVE = [{ value: -1, text: 'Alive' }, ...YEAR_OPTIONS_UNKNOWN]
const yearOptions = (includeAlive, includeUnknown) => {
  if (includeAlive) {
    return YEAR_OPTIONS_ALIVE
  } else if (includeUnknown) {
    return YEAR_OPTIONS_UNKNOWN
  }
  return YEAR_OPTIONS
}

export const YearSelector = ({ includeAlive, includeUnknown, ...props }) =>
  <Select search inline options={yearOptions(includeAlive, includeUnknown)} {...props} />

YearSelector.propTypes = {
  includeAlive: PropTypes.bool,
  includeUnknown: PropTypes.bool,
}

const InlineFormGroup = styled(Form.Group).attrs({ inline: true })`
  flex-wrap: ${props => (props.widths ? 'inherit' : 'wrap')};
  margin: ${props => props.margin || '0em 0em 1em'} !important;
`

export const CheckboxGroup = React.memo((props) => {
  const { value, options, label, groupLabel, onChange, ...baseProps } = props
  return (
    <List>
      <List.Item>
        <List.Header>
          <BaseSemanticInput
            {...baseProps}
            inputType="Checkbox"
            checked={value.length === options.length}
            indeterminate={value.length > 0 && value.length < options.length}
            label={groupLabel || label}
            onChange={({ checked }) => {
              if (checked) {
                onChange(options.map(option => option.value))
              } else {
                onChange([])
              }
            }}
          />
        </List.Header>
        <List.List>
          {options.map(option =>
            <List.Item key={option.value}>
              <BaseSemanticInput
                {...baseProps}
                inputType="Checkbox"
                checked={value.includes(option.value)}
                label={helpLabel(option.text, option.description)}
                onChange={({ checked }) => {
                  if (checked) {
                    onChange([...value, option.value])
                  } else {
                    onChange(value.filter(val => val !== option.value))
                  }
                }}
              />
            </List.Item>,
          )}
        </List.List>
      </List.Item>
    </List>
  )
})

CheckboxGroup.propTypes = {
  value: PropTypes.any,
  options: PropTypes.array,
  onChange: PropTypes.func,
  label: PropTypes.node,
  groupLabel: PropTypes.string,
  horizontalGrouped: PropTypes.bool,
}

export const AlignedCheckboxGroup = styled(CheckboxGroup)`
  text-align: left;
`

const BaseRadioGroup = React.memo((props) => {
  const { value, options, label, onChange, margin, widths, getOptionProps, formGroupAs, ...baseProps } = props
  return (
    <InlineFormGroup margin={margin} widths={widths} as={formGroupAs}>
      {/* eslint-disable-next-line jsx-a11y/label-has-for */}
      {label && <label>{label}</label>}
      {options.map((option, i) =>
        <BaseSemanticInput
          {...baseProps}
          {...getOptionProps(option, value, onChange, i)}
          key={option.value}
          inline
          inputType="Radio"
        />,
      )}
    </InlineFormGroup>
  )
})

BaseRadioGroup.propTypes = {
  value: PropTypes.any,
  options: PropTypes.array,
  onChange: PropTypes.func,
  label: PropTypes.node,
  formGroupAs: PropTypes.any,
  margin: PropTypes.string,
  widths: PropTypes.string,
  getOptionProps: PropTypes.func,
}

const getRadioOptionProps = (option, value, onChange) => ({
  checked: value === option.value,
  label: option.text,
  onChange: ({ checked }) => {
    if (checked) {
      onChange(option.value)
    }
  },
})

export const RadioGroup = React.memo((props) => {
  return <BaseRadioGroup getOptionProps={getRadioOptionProps} {...props} />
})

const getButtonRadioOptionProps = label => (option, value, onChange, i) => ({
  active: value === option.value,
  basic: value !== option.value,
  color: value === option.value ? (option.color || 'grey') : 'black',
  content: option.text,
  label: i === 0 ? label : option.label,
  labelPosition: (label && i === 0) ? 'left' : undefined,
  onClick: (e) => {
    e.preventDefault()
    onChange(option.value)
  },
})

const RadioButtonGroup = styled(({ radioLabelStyle, ...props }) => <Button.Group {...props} />)`
  .left.labeled.button:not(:last-child) {
    .button:last-child {
      border-radius: 0;
    }
  }
  
  ${props => (props.radioLabelStyle ?
    `.label {
      ${props.radioLabelStyle}
    }` : '')}
  
`

export const ButtonRadioGroup = React.memo(({ label, radioLabelStyle, ...props }) => {
  const formGroupAs = groupProps => <RadioButtonGroup radioLabelStyle={radioLabelStyle} {...groupProps} />
  return <BaseRadioGroup as={Button} formGroupAs={formGroupAs} getOptionProps={getButtonRadioOptionProps(label)} {...props} />
})

ButtonRadioGroup.propTypes = {
  label: PropTypes.string,
  radioLabelStyle: PropTypes.string,
}

export const BooleanCheckbox = React.memo((props) => {
  const { value, onChange, ...baseProps } = props
  return <BaseSemanticInput
    {...baseProps}
    inputType="Checkbox"
    checked={Boolean(value)}
    onChange={data => onChange(data.checked)}
  />
})

BooleanCheckbox.propTypes = {
  value: PropTypes.any,
  onChange: PropTypes.func,
}

const BaseInlineToggle = styled(({ divided, fullHeight, asFormInput, ...props }) => <BooleanCheckbox {...props} toggle inline />)`
  ${props => (props.asFormInput ?
    `label {
      font-weight: 700;
    }` : 'margin-bottom: 0 !important;')}
  
  &:last-child {
    padding-right: 0 !important;
  }
  
  ${props => (props.divided ?
    `&:after {
      content: "|";
      padding-left: 10px;
      font-weight: bold;
  }` : '')}
  
  .ui.toggle.checkbox label {
    font-size: small;
    padding: 0 4.5em 0 0;
  }
  
  .ui.toggle.checkbox, .ui.toggle.checkbox input, .ui.toggle.checkbox label, .ui.toggle.checkbox label:before, .ui.toggle.checkbox label:after {
    left: auto !important;
    right: 0  !important;
    ${props => (props.fullHeight ? '' : 'height: 1.2em !important;')}
    min-height: 1.2em !important;
  }
  
  .ui.toggle.checkbox input:checked ~ label:before {
    background-color: ${props => `${props.color || '#2185D0'} !important`};
    right: 0.1em !important;
  }
  
  .ui.toggle.checkbox input:not(:checked) ~ label:after {
    right: 2em !important;
  }
`
// This notation required to fix a ref forwarding bug with styled components and seamntic ui: https://github.com/Semantic-Org/Semantic-UI-React/issues/3786#issuecomment-557560471
export const InlineToggle = props => <BaseInlineToggle {...props} />

export const LabeledSlider = styled(Slider).attrs(props => ({
  handleLabel: `${props.valueLabel !== undefined ? props.valueLabel : (props.value || '')}`,
  labels: { [props.min]: props.minLabel || props.min, [props.max]: props.maxLabel || props.max },
  tooltip: false,
}))`
  width: 100%;

  .rangeslider__fill {
    background-color: grey !important;
    ${props => props.value < 0 && 'width: 0 !important;'}
  }

  .rangeslider__handle {
    z-index: 1;
    
    ${props => props.value < 0 && 'left: calc(100% - 1em) !important;'}
    
    .rangeslider__handle-label {
      text-align: center;
      margin-top: .3em;
      font-size: .9em;
    }
    
    &:after {
      display: none;
    }
  }
  
  .rangeslider__labels .rangeslider__label-item {
    top: -0.8em;
  }
`

export const StepSlider = React.memo(({ steps, stepLabels, value, onChange, ...props }) =>
  <LabeledSlider
    {...props}
    min={0}
    minLabel={stepLabels[steps[0]] || steps[0]}
    max={steps.length - 1}
    maxLabel={stepLabels[steps.length - 1] || steps[steps.length - 1]}
    value={steps.indexOf(value)}
    valueLabel={steps.indexOf(value) >= 0 ? (stepLabels[value] || value) : ''}
    onChange={val => onChange(steps[val])}
  />,
)


StepSlider.propTypes = {
  value: PropTypes.any,
  steps: PropTypes.array,
  stepLabels: PropTypes.object,
  onChange: PropTypes.func,
}

export const Pagination = React.memo(({ onChange, value, error, ...props }) =>
  <PaginationComponent
    activePage={value}
    onPageChange={(e, data) => onChange(data.activePage)}
    {...props}
  />,
)

Pagination.propTypes = {
  value: PropTypes.number,
  onChange: PropTypes.func,
  error: PropTypes.bool,
}

const JSON_EDITOR_MODES = ['code', 'tree']
export const JsonInput = React.memo(({ value, onChange }) =>
  <JsonEditor value={value} onChange={onChange} allowedModes={JSON_EDITOR_MODES} mode="code" search={false} />,
)

JsonInput.propTypes = {
  value: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
  onChange: PropTypes.func,
}
