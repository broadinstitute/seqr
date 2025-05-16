import React from 'react'
import { connect } from 'react-redux'
import PropTypes from 'prop-types'
import { FormSpy } from 'react-final-form'
import styled from 'styled-components'
import { Form, Accordion, Header, Segment, Grid, Icon } from 'semantic-ui-react'

import { getElasticsearchEnabled } from 'redux/selectors'
import { VerticalSpacer } from 'shared/components/Spacers'
import { ButtonLink } from 'shared/components/StyledComponents'
import { configuredField, configuredFields } from 'shared/components/form/FormHelpers'

import {
  INHERITANCE_PANEL,
  PATHOGENICITY_PANEL,
  ANNOTATION_PANEL,
  ANNOTATION_SECONDARY_PANEL,
  IN_SILICO_PANEL,
  FREQUENCY_PANEL,
  LOCATION_PANEL,
  QUALITY_PANEL,
  EXCLUDE_PANEL,
  ANNOTATION_SECONDARY_NAME,
  PATHOGENICITY_PANEL_NAME,
  HGMD_HEADER_INPUT_PROPS,
} from './VariantSearchFormPanelConfigs'
import {
  HGMD_PATHOGENICITY_FIELDS,
  ALL_RECESSIVE_INHERITANCE_FILTERS,
} from '../constants'
import { getDatasetTypes, getHasHgmdPermission } from '../selectors'

const ToggleHeader = styled(Header).attrs({ size: 'huge', block: true })`
  margin-top: 0px !important;

  .dropdown.icon {
    vertical-align: middle !important;
  }

  .grid {
    display: inline-block !important;
    width: calc(100% - 2em);
  }
`

const ToggleHeaderFieldColumn = styled(Grid.Column)`
  font-size: 0.75em;
      
  .fields {
    margin: 0 !important;
    
    &.inline .field:last-child {
      padding-right: 0 !important;
    }
  }
  
  .inline.field  {
    padding-right: 0 !important;
  }
      
  .dropdown {
    &.fluid {
      width: 100% !important;
    }
    
    >.icon {
      margin: -0.75em !important;
      transform: rotate(90deg) !important;
    }
  }
      
  .rangeslider {
    margin: 1.2em;
    font-weight: 300;
    font-size: .9em;
    
    .rangeslider__labels {
      font-size: .5em;
    }
  }
`

const ExpandCollapseCategoryContainer = styled.span`
  float: right;
  position: relative;
  top: -2em;
`

const PANELS = [
  INHERITANCE_PANEL,
  PATHOGENICITY_PANEL,
  ANNOTATION_PANEL,
  ANNOTATION_SECONDARY_PANEL,
  IN_SILICO_PANEL,
  FREQUENCY_PANEL,
  LOCATION_PANEL,
  QUALITY_PANEL,
  EXCLUDE_PANEL,
]

const stopPropagation = e => e.stopPropagation()

const HeaderContent = React.memo(({ name, title, inputSize, inputProps, esEnabled }) => (
  <Grid>
    <Grid.Row>
      <Grid.Column width={inputSize ? 16 - inputSize : 8} verticalAlign="middle">{title}</Grid.Column>
      {inputProps && (
        <ToggleHeaderFieldColumn width={inputSize || 3} floated="right" textAlign="right" onClick={stopPropagation}>
          {configuredField({ ...inputProps, name: `search.${name}`, esEnabled })}
        </ToggleHeaderFieldColumn>
      )}
    </Grid.Row>
  </Grid>
))

HeaderContent.propTypes = {
  title: PropTypes.string.isRequired,
  name: PropTypes.string,
  inputSize: PropTypes.number,
  inputProps: PropTypes.object,
  esEnabled: PropTypes.bool,
}

const searchFieldName = (name, field) => (field.fullFieldValue ? `search.${name}` : `search.${name}.${field.name}`)

const PanelContent = React.memo(({
  name, fields, fieldProps, helpText, fieldLayout, fieldLayoutInput, esEnabled, noPadding, datasetTypes,
  datasetTypeFields, datasetTypeFieldLayoutInput, esEnabledFields, esEnabledDatasetTypeFields,
}) => {
  const layoutInput = (datasetTypeFieldLayoutInput || {})[datasetTypes] || fieldLayoutInput
  const currentDatasetTypeFields = esEnabled ? (esEnabledDatasetTypeFields || datasetTypeFields) : datasetTypeFields
  const panelFields = (currentDatasetTypeFields || {})[datasetTypes] || (esEnabled && esEnabledFields) || fields
  const fieldComponents = panelFields && configuredFields(
    { fields: panelFields.map(field => ({ ...(fieldProps || {}), ...field, name: searchFieldName(name, field) })) },
  )
  return (
    <div>
      {helpText && (
        <i>
          {helpText}
          <VerticalSpacer height={20} />
        </i>
      )}
      <Form.Group widths="equal">
        {!noPadding && <Form.Field width={2} />}
        {fieldLayout ? fieldLayout(fieldComponents, layoutInput) : fieldComponents}
        {!noPadding && <Form.Field width={2} />}
      </Form.Group>
    </div>
  )
})

PanelContent.propTypes = {
  fields: PropTypes.arrayOf(PropTypes.object),
  name: PropTypes.string.isRequired,
  fieldProps: PropTypes.object,
  datasetTypes: PropTypes.string,
  datasetTypeFields: PropTypes.object,
  helpText: PropTypes.node,
  fieldLayout: PropTypes.func,
  fieldLayoutInput: PropTypes.arrayOf(PropTypes.string),
  datasetTypeFieldLayoutInput: PropTypes.object,
  esEnabled: PropTypes.bool,
  esEnabledFields: PropTypes.arrayOf(PropTypes.object),
  esEnabledDatasetTypeFields: PropTypes.object,
  noPadding: PropTypes.bool,
}

const hasSecondaryAnnotation = inheritance => ALL_RECESSIVE_INHERITANCE_FILTERS.includes(inheritance?.mode)

class VariantSearchFormPanels extends React.PureComponent {

  static propTypes = {
    esEnabled: PropTypes.bool,
    hasHgmdPermission: PropTypes.bool,
    inheritance: PropTypes.string,
    datasetTypes: PropTypes.string,
  }

  state = { active: {} }

  expandAll = (e) => {
    e.preventDefault()
    this.setState({ active: PANELS.reduce((acc, { name }) => ({ ...acc, [name]: true }), {}) })
  }

  collapseAll = (e) => {
    e.preventDefault()
    this.setState({ active: {} })
  }

  handleTitleClick = name => () => {
    const { active } = this.state
    this.setState({ active: { ...active, [name]: !active[name] } })
  }

  render() {
    const { esEnabled, hasHgmdPermission, inheritance, datasetTypes } = this.props
    const { active } = this.state
    return (
      <div>
        <ExpandCollapseCategoryContainer>
          <ButtonLink onClick={this.expandAll}>
            Expand All &nbsp;
            <Icon name="plus" />
          </ButtonLink>
          <b>| &nbsp;&nbsp;</b>
          <ButtonLink onClick={this.collapseAll}>
            Collapse All &nbsp;
            <Icon name="minus" />
          </ButtonLink>
        </ExpandCollapseCategoryContainer>
        <VerticalSpacer height={10} />
        <Accordion fluid exclusive={false}>
          {PANELS.reduce((acc, { name, headerProps, fields, ...panelContentProps }, i) => {
            if (name === ANNOTATION_SECONDARY_NAME && !hasSecondaryAnnotation(inheritance)) {
              return acc
            }
            const showHgmd = name === PATHOGENICITY_PANEL_NAME && hasHgmdPermission
            const isActive = !!active[name]
            let attachedTitle = true
            if (i === 0) {
              attachedTitle = 'top'
            } else if (i === PANELS.length - 1 && !isActive) {
              attachedTitle = 'bottom'
            }
            return [...acc,
              <Accordion.Title
                key={`${name}-title`}
                active={isActive}
                index={i}
                onClick={this.handleTitleClick(name)}
                as={ToggleHeader}
                attached={attachedTitle}
              >
                <Icon name="dropdown" />
                <HeaderContent
                  name={name}
                  esEnabled={esEnabled}
                  inputProps={showHgmd ? HGMD_HEADER_INPUT_PROPS : headerProps.inputProps}
                  {...headerProps}
                />
              </Accordion.Title>,
              <Accordion.Content
                key={`${name}-content`}
                active={isActive}
                as={Segment}
                attached={i === PANELS.length - 1 ? 'bottom' : true}
                padded
                textAlign="center"
              >
                <PanelContent
                  name={name}
                  esEnabled={esEnabled}
                  datasetTypes={datasetTypes}
                  fields={showHgmd ? HGMD_PATHOGENICITY_FIELDS : fields}
                  {...panelContentProps}
                />
              </Accordion.Content>,
            ]
          }, [])}
        </Accordion>
      </div>
    )
  }

}

const mapStateToProps = (state, ownProps) => ({
  hasHgmdPermission: getHasHgmdPermission(state, ownProps),
  datasetTypes: getDatasetTypes(state, ownProps),
  esEnabled: getElasticsearchEnabled(state),
})

const ConnectedVariantSearchFormPanels = connect(mapStateToProps)(VariantSearchFormPanels)

const SUBSCRIPTION = { values: true }

export default props => (
  <FormSpy subscription={SUBSCRIPTION}>
    {({ values }) => (
      <ConnectedVariantSearchFormPanels
        {...props}
        projectFamilies={values.projectFamilies}
        inheritance={values.search?.inheritance}
      />
    )}
  </FormSpy>
)
