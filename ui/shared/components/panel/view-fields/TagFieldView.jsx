import React from 'react'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup, Form } from 'semantic-ui-react'
import { Field } from 'react-final-form'

import { getHpoTermOptionsByFamily } from 'redux/selectors'
import { HorizontalSpacer } from '../../Spacers'
import { ColoredLabel, ColoredOutlineLabel } from '../../StyledComponents'
import { LargeMultiselect, Multiselect } from '../../form/Inputs'
import OptionFieldView from './OptionFieldView'

const NOTES_METADATA_TITLE = 'Notes'

const MODAL_STYLE = { minHeight: 'calc(90vh - 100px)' }

const TAG_FIELD_PROPS = { component: LargeMultiselect, defaultOpen: true }

const MetadataFormGroup = styled(Form.Group).attrs({ inline: true })`
  label, .label {
    white-space: nowrap;
  }
  
  .fluid.selection.dropdown {
    width: 100% !important;
  } 
`

const MultiselectField = ({ input, ...props }) => <Multiselect {...input} {...props} />

MultiselectField.propTypes = {
  input: PropTypes.object,
}

const mapHpoDropdownStateToProps = (state, ownProps) => ({
  options: getHpoTermOptionsByFamily(state)[ownProps.metadataId],
})

const LIST_FORMAT_PROPS = {
  format: val => (val || '').split(', ').filter(v => v),
  parse: val => (val || []).join(', '),
}

const METADATA_FIELD_PROPS = {
  [NOTES_METADATA_TITLE]: { width: 16, maxLength: 50, placeholder: 'Enter up to 50 characters' },
  Name: { width: 16, maxLength: 100, placeholder: 'Enter up to 100 characters' },
  Reason: { width: 16, maxLength: 50, placeholder: 'Brief reason for excluding. Enter up to 50 characters' },
  'Test Type(s)': {
    width: 16,
    component: MultiselectField,
    fluid: true,
    allowAdditions: true,
    addValueOptions: true,
    options: ['Sanger', 'Segregation', 'SV', 'Splicing'].map(value => ({ value })),
    placeholder: 'Select test types or add your own',
    ...LIST_FORMAT_PROPS,
  },
  'HPO Terms': {
    width: 16,
    component: connect(mapHpoDropdownStateToProps)(MultiselectField),
    ...LIST_FORMAT_PROPS,
  },
}

const MetadataField = React.memo(({ value, name, error, metadataId }) => {
  if (!value.metadataTitle) {
    return null
  }
  const label = <ColoredOutlineLabel color={value.color} content={value.name} size="large" pointing="right" basic />
  const fieldProps = METADATA_FIELD_PROPS[value.metadataTitle] || { width: 4, type: 'number', min: 0 }
  return (
    <MetadataFormGroup>
      {value.description ? <Popup trigger={label} content={value.description} /> : label}
      <Field
        name={`${name}.metadata`}
        component={Form.Input}
        label={value.metadataTitle}
        error={error}
        metadataId={metadataId}
        {...fieldProps}
      />
    </MetadataFormGroup>
  )
})

MetadataField.propTypes = {
  value: PropTypes.object,
  name: PropTypes.string,
  error: PropTypes.bool,
  metadataId: PropTypes.string,
}

export const TagFieldDisplay = React.memo(({
  displayFieldValues, tagAnnotation, popup, displayAnnotationFirst, displayMetadata, linkTagType, tagLinkUrl, tagLookup,
}) => (
  <span>
    {displayFieldValues.map((initialTag) => {
      const tag = tagLookup ? tagLookup[initialTag] : initialTag
      let content = tag.name || tag.text
      if (displayMetadata && tag.metadata) {
        content = `${content}: ${tag.metadata}`
      }
      const baseLabel = <ColoredLabel size="small" color={tag.color} horizontal content={content} />
      const label = (linkTagType && linkTagType === tag.name) ?
        <NavLink to={tagLinkUrl}>{baseLabel}</NavLink> : baseLabel
      const annotation = tagAnnotation && tagAnnotation(tag)
      return (
        <span key={tag.tagGuid || tag.name}>
          <HorizontalSpacer width={5} />
          {displayAnnotationFirst && annotation}
          {popup ? popup(tag)(label, displayMetadata) : label}
          {!displayAnnotationFirst && annotation}
        </span>
      )
    })}
  </span>
))

TagFieldDisplay.propTypes = {
  displayFieldValues: PropTypes.arrayOf(PropTypes.oneOfType(PropTypes.object, PropTypes.string)).isRequired,
  popup: PropTypes.func,
  tagAnnotation: PropTypes.func,
  displayAnnotationFirst: PropTypes.bool,
  displayMetadata: PropTypes.bool,
  linkTagType: PropTypes.string,
  tagLinkUrl: PropTypes.string,
  tagLookup: PropTypes.object,
}

class TagFieldView extends React.PureComponent {

  static propTypes = {
    field: PropTypes.string.isRequired,
    idField: PropTypes.string.isRequired,
    initialValues: PropTypes.object,
    tagOptions: PropTypes.arrayOf(PropTypes.object).isRequired,
    fieldValue: PropTypes.arrayOf(PropTypes.object),
    onSubmit: PropTypes.func.isRequired,
    displayMetadata: PropTypes.bool,
    popup: PropTypes.func,
    tagAnnotation: PropTypes.func,
    simplifiedValue: PropTypes.bool,
    validate: PropTypes.func,
    disabledTagType: PropTypes.string,
    noEditTagTypes: PropTypes.arrayOf(PropTypes.string),
    linkTagType: PropTypes.string,
    tagLinkUrl: PropTypes.string,
    modalId: PropTypes.string,
  }

  getSimplifiedProps() {
    const { initialValues } = this.props
    return { initialValues, formFieldProps: TAG_FIELD_PROPS, tagOptions: this.tagSelectOptions() }
  }

  getMappedProps() {
    const { field, initialValues, validate, noEditTagTypes } = this.props

    const fieldValues = this.fieldValues()
    const tagSelectOptions = this.tagSelectOptions()

    const tagOptionsMap = tagSelectOptions.reduce((acc, tag) => ({ [tag.name]: tag, ...acc }), {})

    const mappedValues = {
      ...initialValues,
      [field]: fieldValues.map(tag => tagOptionsMap[tag.name]).sort((a, b) => a.optionIndex - b.optionIndex),
    }

    const formFieldProps = {
      ...TAG_FIELD_PROPS,
      parse: value => value.map(option => tagOptionsMap[option]),
      format: options => options.map(tag => tag.name),
    }
    if (validate) {
      formFieldProps.validate = validate
    }

    const tagOptions = noEditTagTypes ? tagSelectOptions.filter(
      ({ name }) => !noEditTagTypes.includes(name),
    ) : tagSelectOptions

    return { initialValues: mappedValues, formFieldProps, tagOptions }
  }

  fieldValues = () => {
    const { fieldValue, field, initialValues } = this.props
    return fieldValue || (initialValues || {})[field] || []
  }

  tagSelectOptions = () => {
    const { tagOptions, disabledTagType } = this.props
    const fieldValues = this.fieldValues()

    return tagOptions.reduce((acc, tag, i) => {
      const fieldValue = fieldValues.find(val => val.name === tag.name)
      if (disabledTagType && tag.name === disabledTagType && !fieldValue) {
        return acc
      }
      return [...acc, { ...tag, ...fieldValue, optionIndex: i }]
    }, [])
  }

  fieldDisplay = (displayFieldValues) => {
    const { popup, tagAnnotation, displayMetadata, linkTagType, tagLinkUrl } = this.props
    return (
      <TagFieldDisplay
        displayFieldValues={displayFieldValues}
        popup={popup}
        tagAnnotation={tagAnnotation}
        displayMetadata={displayMetadata}
        linkTagType={linkTagType}
        tagLinkUrl={tagLinkUrl}
      />
    )
  }

  render() {
    const {
      simplifiedValue, field, tagOptions, popup, tagAnnotation, validate, displayMetadata, modalId, ...props
    } = this.props

    const additionalFields = tagOptions.some(({ metadataTitle }) => metadataTitle) ? [{
      name: field,
      key: 'test',
      isArrayField: true,
      validate: val => ((!val || !val.metadataTitle || val.metadataTitle === NOTES_METADATA_TITLE || val.metadata) ? undefined : 'Required'),
      component: MetadataField,
      metadataId: modalId,
    }] : []

    return (
      <OptionFieldView
        field={field}
        additionalEditFields={additionalFields}
        modalStyle={MODAL_STYLE}
        fieldDisplay={this.fieldDisplay}
        modalId={modalId}
        {...props}
        {...(simplifiedValue ? this.getSimplifiedProps() : this.getMappedProps())}
      />
    )
  }

}

export default TagFieldView
