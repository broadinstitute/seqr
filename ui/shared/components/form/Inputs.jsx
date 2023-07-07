/* eslint-disable max-classes-per-file */

import React, { createElement } from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import {
  Form, List, Button, Pagination as PaginationComponent, Search, Dropdown as DropdownComponent, Header,
} from 'semantic-ui-react'

import { helpLabel } from './FormHelpers'

const optionsAreEqual = (options, nextOptions) => {
  if (nextOptions) {
    if (nextOptions.length !== (options || []).length) {
      return false
    }
    if (Object.entries(nextOptions)
      .some(([i, opt]) => ['value', 'text', 'color', 'disabled', 'description']
        .some(k => opt[k] !== options[i][k]))
    ) {
      return false
    }
  }
  return true
}

const hasUpdatedFormInputProps = (props, nextProps) => {
  if (!optionsAreEqual(props.options, nextProps.options)) {
    return false
  }
  if (Object.keys(nextProps).filter(k => k !== 'onChange' && k !== 'options').some(
    k => nextProps[k] !== props[k],
  )) {
    return false
  }
  return true
}

const formInputComponentShouldUpdate = (that, nextProps, nextState) => {
  if (!hasUpdatedFormInputProps(that.props, nextProps)) {
    return true
  }
  return nextState !== that.state
}
export class BaseSemanticInput extends React.Component {

  static propTypes = {
    onChange: PropTypes.func,
    inputType: PropTypes.string.isRequired,
    options: PropTypes.arrayOf(PropTypes.object),
  }

  shouldComponentUpdate(nextProps, nextState) {
    return formInputComponentShouldUpdate(this, nextProps, nextState)
  }

  handleChange = (e, data) => {
    const { onChange } = this.props
    onChange(data.value === undefined ? data : data.value)
  }

  render() {
    const { inputType, ...props } = this.props
    return createElement(Form[inputType], { ...props, onChange: this.handleChange, onBlur: null })
  }

}

const setIntVal = (onChange, min, max) => (stringVal) => {
  if (stringVal === '') {
    onChange(null)
  }
  const val = parseInt(stringVal, 10)
  if ((min === undefined || val >= min) && (max === undefined || val <= max)) {
    onChange(val)
  }
}

export const IntegerInput = React.memo(({ onChange, min, max, value, ...props }) => (
  <BaseSemanticInput
    {...props}
    value={Number.isInteger(value) ? value : ''}
    inputType="Input"
    type="number"
    min={min}
    max={max}
    onChange={setIntVal(onChange, min, max)}
  />
))

IntegerInput.propTypes = {
  onChange: PropTypes.func,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  min: PropTypes.number,
  max: PropTypes.number,
}

const DisabledItem = styled(DropdownComponent.Item).attrs({ disabled: true })`
  &:hover {
    background: inherit !important;
  }
`

const labelStyle = color => (color ? { color: 'white', backgroundColor: color } : {})

const styledOption = option => ({
  value: option.value,
  key: option.key || option.text || option.value,
  text: option.text || option.name || option.value,
  label: option.color ? { empty: true, circular: true, style: labelStyle(option.color) } : null,
  color: option.color,
  disabled: option.disabled,
  description: option.description,
  icon: option.icon,
})

const processOptions = (options, includeCategories) => {
  let currCategory = null
  return options.reduce((acc, option) => {
    if (includeCategories && option.category !== currCategory) {
      currCategory = option.category
      if (option.category) {
        acc.push({
          as: DisabledItem,
          key: option.category,
          content: <Header content={option.category} size="tiny" dividing />,
        })
      }
    }
    acc.push(styledOption(option))
    return acc
  }, [])
}

export const Dropdown = React.memo(({ options, includeCategories, ...props }) => (
  <BaseSemanticInput
    {...props}
    inputType="Dropdown"
    options={processOptions(options, includeCategories)}
    noResultsMessage={null}
    tabIndex="0"
  />
))

Dropdown.propTypes = {
  options: PropTypes.arrayOf(PropTypes.object),
  includeCategories: PropTypes.bool,
}

export const Select = props => <Dropdown selection fluid {...props} />

Select.propTypes = {
  options: PropTypes.arrayOf(PropTypes.object),
}

export class Multiselect extends React.PureComponent {

  static propTypes = {
    color: PropTypes.string,
    allowAdditions: PropTypes.bool,
  }

  renderLabel = (data) => {
    const { color } = this.props
    return { color, content: data.text || data.value, style: labelStyle(data.color) }
  }

  render() {
    const { allowAdditions, ...props } = this.props
    return (
      <AddableSelect
        {...props}
        renderLabel={this.renderLabel}
        allowAdditions={allowAdditions || false}
        multiple
      />
    )
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
    options: PropTypes.arrayOf(PropTypes.object),
    allowAdditions: PropTypes.bool,
    addValueOptions: PropTypes.bool,
    value: PropTypes.arrayOf(PropTypes.string),
  }

  constructor(props) {
    super(props)

    let { options } = props
    if (props.addValueOptions && props.value) {
      const valueOptions = props.value.filter(
        val => !props.options.some(({ value }) => value === val),
      ).map(value => ({ value }))
      options = [...options, ...valueOptions]
    }
    this.state = { options } // eslint-disable-line react/state-in-constructor
  }

  componentDidUpdate(prevProps) {
    const { options } = this.props
    if (options.length !== prevProps.options.length) {
      this.resetOptions()
    }
  }

  resetOptions = () => {
    const { options } = this.props
    this.setState({ options })
  }

  handleAddition = (e, { value }) => {
    this.setState(prevState => ({
      options: [{ value }, ...prevState.options],
    }))
  }

  render() {
    const { addValueOptions, ...props } = this.props
    const { options } = this.state
    return (
      <Select
        {...props}
        options={options}
        allowAdditions={props.allowAdditions !== false}
        onAddItem={this.handleAddition}
        search
      />
    )
  }

}

export class SearchInput extends React.PureComponent {

  static propTypes = {
    onChange: PropTypes.func,
    options: PropTypes.arrayOf(PropTypes.object),
  }

  state = { results: null }

  handleResultSelect = (e, { result }) => {
    const { onChange } = this.props
    onChange(e, result.title)
  }

  handleSearchChange = (e, data) => {
    const { options, onChange } = this.props
    this.setState({
      results: options.filter(({ title }) => title.toLowerCase().includes(data.value.toLowerCase())),
    })
    onChange(e, data)
  }

  render() {
    const { options, onChange, ...props } = this.props
    const { results } = this.state
    return (
      <Search
        {...props}
        results={results || options}
        onResultSelect={this.handleResultSelect}
        onSearchChange={this.handleSearchChange}
      />
    )
  }

}

const YEAR_OPTIONS = [...Array(130).keys()].map(i => ({ value: i + 1900 }))
const YEAR_OPTIONS_UNKNOWN = [{ value: 0, text: 'Unknown' }, ...YEAR_OPTIONS]
const YEAR_OPTIONS_ALIVE = [{ value: -1, text: 'Alive' }, ...YEAR_OPTIONS_UNKNOWN]
const yearOptions = (includeAlive, includeUnknown) => {
  if (includeAlive) {
    return YEAR_OPTIONS_ALIVE
  }
  if (includeUnknown) {
    return YEAR_OPTIONS_UNKNOWN
  }
  return YEAR_OPTIONS
}

export const YearSelector = ({ includeAlive, includeUnknown, ...props }) => (
  <Select search inline options={yearOptions(includeAlive, includeUnknown)} {...props} />)

YearSelector.propTypes = {
  includeAlive: PropTypes.bool,
  includeUnknown: PropTypes.bool,
}

const InlineFormGroup = styled(Form.Group).attrs({ inline: true })`
  flex-wrap: ${props => (props.widths ? 'inherit' : 'wrap')};
  margin: ${props => props.margin || '0em 0em 1em'} !important;
`

const selectAll = (onChange, value, options) => ({ checked }) => {
  const remainValue = value.filter(val => !options.find(opt => opt.value === val))
  if (checked) {
    onChange(options.map(option => option.value).concat(remainValue))
  } else {
    onChange(remainValue)
  }
}

const selectCheckbox = (onChange, value, option) => ({ checked }) => {
  if (checked) {
    onChange([...value, option.value])
  } else {
    onChange(value.filter(val => val !== option.value))
  }
}

export const CheckboxGroup = React.memo((props) => {
  const { value, label, groupLabel, onChange, ...baseProps } = props
  const options = props.options.map(styledOption)
  const numSelected = options.filter(opt => value.includes(opt.value)).length
  return (
    <List>
      <List.Item>
        <List.Header>
          <BaseSemanticInput
            {...baseProps}
            inputType="Checkbox"
            checked={numSelected === options.length}
            indeterminate={numSelected > 0 && numSelected < options.length}
            label={groupLabel || label}
            onChange={selectAll(onChange, value, options)}
          />
        </List.Header>
        <List.List>
          {options.map(option => (
            <List.Item key={option.key}>
              <BaseSemanticInput
                {...baseProps}
                inputType="Checkbox"
                checked={value.includes(option.value)}
                label={helpLabel(option.text, option.description)}
                onChange={selectCheckbox(onChange, value, option)}
              />
            </List.Item>
          ))}
        </List.List>
      </List.Item>
    </List>
  )
})

CheckboxGroup.propTypes = {
  value: PropTypes.any, // eslint-disable-line react/forbid-prop-types
  options: PropTypes.arrayOf(PropTypes.object),
  onChange: PropTypes.func,
  label: PropTypes.node,
  groupLabel: PropTypes.node,
  horizontalGrouped: PropTypes.bool,
}

export const AlignedCheckboxGroup = styled(CheckboxGroup)`
  text-align: left;
`

const BaseRadioGroup = React.memo((props) => {
  const { value, options, label, onChange, margin, widths, getOptionProps, formGroupAs, grouped, ...baseProps } = props
  return (
    <InlineFormGroup margin={margin} widths={widths} as={formGroupAs} grouped={grouped}>
      {label && <label>{label}</label>}
      {options.map((option, i) => (
        <BaseSemanticInput
          {...baseProps}
          {...getOptionProps(option, value, onChange, i)}
          key={option.value}
          inline
          inputType="Radio"
        />
      ))}
    </InlineFormGroup>
  )
})

BaseRadioGroup.propTypes = {
  value: PropTypes.any, // eslint-disable-line react/forbid-prop-types
  options: PropTypes.arrayOf(PropTypes.object),
  onChange: PropTypes.func,
  label: PropTypes.node,
  formGroupAs: PropTypes.elementType,
  margin: PropTypes.string,
  widths: PropTypes.string,
  grouped: PropTypes.bool,
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

export const RadioGroup = React.memo(props => <BaseRadioGroup getOptionProps={getRadioOptionProps} {...props} />)

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

export const RadioButtonGroup = styled(({ radioLabelStyle, ...props }) => <Button.Group {...props} />)`
  .left.labeled.button:not(:last-child) {
    .button:last-child {
      border-radius: 0;
    }
  }

  &.buttons + .buttons .label {
    margin-left: 1em !important;
  }
  
  ${props => (props.radioLabelStyle ?
    `.label {
      ${props.radioLabelStyle}
    }` : '')}
  
`

export const ButtonRadioGroup = React.memo(({ label, groupContainer, ...props }) => (
  <BaseRadioGroup
    as={Button}
    formGroupAs={groupContainer || RadioButtonGroup}
    getOptionProps={getButtonRadioOptionProps(label)}
    {...props}
  />
))

ButtonRadioGroup.propTypes = {
  label: PropTypes.string,
  groupContainer: PropTypes.elementType,
}

const setBoolVal = onChange => data => onChange(data.checked)

export const BooleanCheckbox = React.memo((props) => {
  const { value, onChange, ...baseProps } = props
  return (
    <BaseSemanticInput
      {...baseProps}
      inputType="Checkbox"
      checked={Boolean(value)}
      onChange={setBoolVal(onChange)}
    />
  )
})

BooleanCheckbox.propTypes = {
  value: PropTypes.any, // eslint-disable-line react/forbid-prop-types
  onChange: PropTypes.func,
}

export const AlignedBooleanCheckbox = AlignedCheckboxGroup.withComponent(BooleanCheckbox)

const BaseInlineToggle = styled(({ divided, fullHeight, asFormInput, padded, ...props }) => <BooleanCheckbox {...props} toggle inline />)`
  ${props => (props.asFormInput ?
    `label {
      font-weight: 700;
    }` : 'margin-bottom: 0 !important;')}
  
  &:last-child {
    padding-right: ${props => (props.padded ? '1em' : '0')} !important;
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

const onPageChange = onChange => (e, data) => onChange(data.activePage)

export const Pagination = React.memo(({ onChange, value, error, ...props }) => (
  <PaginationComponent
    activePage={value}
    onPageChange={onPageChange(onChange)}
    {...props}
  />
))

Pagination.propTypes = {
  value: PropTypes.number,
  onChange: PropTypes.func,
  error: PropTypes.bool,
}
