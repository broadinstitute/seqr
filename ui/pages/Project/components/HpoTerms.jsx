import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Field } from 'react-final-form'
import { Form, Header, Accordion, Icon, Tab } from 'semantic-ui-react'

import { RadioGroup } from 'shared/components/form/Inputs'
import { AwesomeBarFormInput } from 'shared/components/page/AwesomeBar'
import { getHpoTermsForCategory, CATEGORY_NAMES } from 'shared/components/panel/HpoPanel'
import DataLoader from 'shared/components/DataLoader'
import { ButtonLink } from 'shared/components/StyledComponents'
import { VerticalSpacer } from 'shared/components/Spacers'

import { loadHpoTerms } from 'redux/rootReducer'
import { getHpoTermsByParent, getHpoTermsIsLoading } from 'redux/selectors'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'

const ScrollingTab = styled(Tab).attrs({ menu: { attached: true } })`
  .menu.attached {
    overflow-x: scroll;
  }
  
  .menu.text {
    margin: .1em -.5em;
  }
`

const getFlattenedHpoTermsByCategory = (features, nonstandardFeatures) => Object.values(getHpoTermsForCategory(
  (features || []).map((term, index) => ({ ...term, index })),
  nonstandardFeatures && nonstandardFeatures.map((term, index) => ({ ...term, index })),
)).reduce((acc, { categoryName, terms }) => [...acc, { ...terms[0], categoryName }, ...terms.slice(1)], [])

const HPO_QUALIFIERS = [
  {
    type: 'age_of_onset',
    options: [
      'Congenital onset',
      'Embryonal onset',
      'Fetal onset',
      'Neonatal onset',
      'Infantile onset',
      'Childhood onset',
      'Juvenile onset',
      'Adult onset',
      'Young adult onset',
      'Middle age onset',
      'Late onset',
    ],
  },
  {
    type: 'pace_of_progression',
    options: ['Nonprogressive', 'Slow progression', 'Progressive', 'Rapidly progressive', 'Variable progression rate'],
  },
  {
    type: 'severity',
    options: ['Borderline', 'Mild', 'Moderate', 'Severe', 'Profound'],
  },
  {
    type: 'temporal_pattern',
    options: ['Insidious onset', 'Chronic', 'Subacute', 'Acute'],
  },
  {
    type: 'spatial_pattern',
    options: ['Generalized', 'Localized', 'Distal', 'Proximal'],
  },
  {
    type: 'laterality',
    options: ['Bilateral', 'Unilateral', 'Left', 'Right'],
  },
]

const updateInput = (input, type) => val => input.onChange(({ ...input.value, [type]: val }))

const HpoQualifiers = ({ input }) => (
  <Accordion
    exclusive={false}
    panels={HPO_QUALIFIERS.map(({ type, options }) => ({
      key: type,
      title: { content: <b>{snakecaseToTitlecase(type)}</b> },
      content: {
        content: (
          <RadioGroup
            onChange={updateInput(input, type)}
            value={input.value[type]}
            options={options.map(value => ({ value, text: value }))}
            margin="0 1em"
          />
        ),
      },
    }))}
  />
)

HpoQualifiers.propTypes = {
  input: PropTypes.object,
}

const formatQualifiers = val => (val || []).reduce((acc, { type, label }) => ({ ...acc, [type]: label }), {})
const normalizeQualifiers = val => Object.entries(val || {}).map(([type, label]) => ({ type, label }))

const HpoTermDetails = React.memo(({ value, name, icon, toggleShowDetails, showDetails }) => (
  <div>
    {value.categoryName ? <Header content={value.categoryName} size="small" /> : null}
    <Form.Group inline>
      <Form.Field width={1}>{icon}</Form.Field>
      <Form.Field width={13}>
        {value.label ? `${value.label} (${value.id})` : value.id}
      </Form.Field>
      <Form.Field width={2}>
        <ButtonLink
          floated="right"
          size="small"
          onClick={toggleShowDetails}
          content={showDetails ? 'Hide Details' : 'Edit Details'}
        />
      </Form.Field>
    </Form.Group>
    {showDetails && [
      <Field
        key="qualifiers"
        name={`${name}.qualifiers`}
        component={HpoQualifiers}
        format={formatQualifiers}
        parse={normalizeQualifiers}
      />,
      <Form.Group key="notes">
        <Field name={`${name}.notes`} placeholder="Comments" component={Form.Input} width={16} />
      </Form.Group>,
    ]}
  </div>
))

HpoTermDetails.propTypes = {
  icon: PropTypes.node,
  value: PropTypes.object,
  name: PropTypes.string,
  showDetails: PropTypes.bool,
  toggleShowDetails: PropTypes.func,
}

const CATEGORY_MENU = { text: true }

const getTermPanes = (term, addItem) => ([{
  menuItem: {
    key: term.id,
    content: term.label,
    icon: { name: 'plus', color: 'green', size: 'large', onClick: () => addItem(term) },
  },
  render: () => <HpoCategory category={term.id} addItem={addItem} />,
}])

const BaseHpoCategory = ({ category, hpoTerms, addItem, ...props }) => (
  <DataLoader contentId={category} content={hpoTerms} reloadOnIdUpdate {...props}>
    {Object.values(hpoTerms || {}).length > 0 && (
      <Tab.Pane attached={false}>
        {Object.values(hpoTerms).map(term => (
          <Tab key={term.id} menu={CATEGORY_MENU} defaultActiveIndex={null} panes={getTermPanes(term, addItem)} />
        ))}
      </Tab.Pane>
    )}
  </DataLoader>
)

BaseHpoCategory.propTypes = {
  category: PropTypes.string,
  hpoTerms: PropTypes.object,
  addItem: PropTypes.func,
}

const mapCategoryStateToProps = (state, ownProps) => {
  const hpoTerms = getHpoTermsByParent(state)[ownProps.category]
  return {
    hpoTerms,
    loading: !hpoTerms && getHpoTermsIsLoading(state),
  }
}

const mapCategoryDispatchToProps = {
  load: loadHpoTerms,
}

const HpoCategory = connect(mapCategoryStateToProps, mapCategoryDispatchToProps)(BaseHpoCategory)

const HPO_CATEGORIES = ['hpo_terms']

const getCategoryPanes = addItem => Object.entries(CATEGORY_NAMES).map(
  ([key, menuItem]) => ({
    key,
    menuItem,
    render: () => <HpoCategory category={key} addItem={addItem} />,
  }),
).sort((a, b) => a.menuItem.localeCompare(b.menuItem))

const parseHpoResult = result => ({ id: result.key, label: result.title, category: result.category })

const HpoTermSelector = ({ addItem }) => (
  <div>
    <AwesomeBarFormInput
      parseResultItem={parseHpoResult}
      categories={HPO_CATEGORIES}
      placeholder="Search for HPO terms"
      onChange={addItem}
    />
    <VerticalSpacer height={10} />
    <ScrollingTab panes={getCategoryPanes(addItem)} defaultActiveIndex={null} />
  </div>
)

HpoTermSelector.propTypes = {
  addItem: PropTypes.func,
}

class HpoTermsEditor extends React.PureComponent {

  static propTypes = {
    value: PropTypes.arrayOf(PropTypes.object),
    name: PropTypes.string,
    onChange: PropTypes.func,
    header: PropTypes.object,
    allowAdditions: PropTypes.bool,
  }

  state = { showDetails: {}, showAddItem: false }

  toggleShowDetails = id => (e) => {
    e.preventDefault()
    this.setState(prevState => ({
      showDetails: { ...prevState.showDetails, [id]: !prevState.showDetails[id] },
    }))
  }

  toggleShowAddItems = (e) => {
    e.preventDefault()
    this.setState(prevState => ({
      showAddItem: !prevState.showAddItem,
    }))
  }

  addItem = (data) => {
    const { onChange, value } = this.props
    onChange([...value, data])
    this.setState({ showAddItem: false })
  }

  removeItem = (e, data) => {
    const { onChange, value } = this.props
    e.preventDefault()
    onChange(value.filter(({ id }) => id !== data.id))
  }

  render() {
    const { value, name, allowAdditions, header } = this.props
    const { showDetails, showAddItem } = this.state
    return (
      <div>
        {header && <Header dividing {...header} />}
        {header && <VerticalSpacer height={5} />}
        {value.map(({ index, ...item }) => (
          <HpoTermDetails
            key={item.id}
            value={item}
            name={`${name}[${index}]`}
            icon={<Icon name="remove" link id={item.id} onClick={this.removeItem} />}
            showDetails={!!showDetails[item.id]}
            toggleShowDetails={this.toggleShowDetails(item.id)}
          />
        ))}
        {allowAdditions && (showAddItem ? <HpoTermSelector addItem={this.addItem} /> :
        <ButtonLink icon="plus" content="Add Feature" onClick={this.toggleShowAddItems} />)}
        {allowAdditions && <VerticalSpacer height={20} />}
      </div>
    )
  }

}

export const HPO_FORM_FIELDS = [ // eslint-disable-line import/prefer-default-export
  {
    name: 'nonstandardFeatures',
    component: HpoTermsEditor,
    format: val => getFlattenedHpoTermsByCategory([], val),
    allowAdditions: false,
    header: { content: 'Present', color: 'green' },
  },
  {
    name: 'features',
    component: HpoTermsEditor,
    format: val => getFlattenedHpoTermsByCategory(val),
    allowAdditions: true,
  },
  {
    name: 'absentNonstandardFeatures',
    component: HpoTermsEditor,
    format: val => getFlattenedHpoTermsByCategory([], val),
    allowAdditions: false,
    header: { content: 'Not Present', color: 'red' },
  },
  {
    name: 'absentFeatures',
    component: HpoTermsEditor,
    format: val => getFlattenedHpoTermsByCategory(val),
    allowAdditions: true,
  },
]
