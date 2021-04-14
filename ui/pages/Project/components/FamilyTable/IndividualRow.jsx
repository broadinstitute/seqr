import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Field } from 'redux-form'
import { Label, Popup, Form, Input, Header, Accordion, Icon, Tab } from 'semantic-ui-react'
import orderBy from 'lodash/orderBy'

import { Select, SearchInput, RadioGroup } from 'shared/components/form/Inputs'
import PedigreeIcon from 'shared/components/icons/PedigreeIcon'
import { AwesomeBarFormInput } from 'shared/components/page/AwesomeBar'
import BaseFieldView from 'shared/components/panel/view-fields/BaseFieldView'
import TagFieldView from 'shared/components/panel/view-fields/TagFieldView'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import ListFieldView from 'shared/components/panel/view-fields/ListFieldView'
import NullableBoolFieldView, { NULLABLE_BOOL_FIELD } from 'shared/components/panel/view-fields/NullableBoolFieldView'
import OptionFieldView from 'shared/components/panel/view-fields/OptionFieldView'
import HpoPanel, { getHpoTermsForCategory, CATEGORY_NAMES } from 'shared/components/panel/HpoPanel'
import Sample from 'shared/components/panel/sample'
import { FamilyLayout } from 'shared/components/panel/family'
import DataLoader from 'shared/components/DataLoader'
import { ColoredIcon, ButtonLink } from 'shared/components/StyledComponents'
import { VerticalSpacer } from 'shared/components/Spacers'
import { AFFECTED, PROBAND_RELATIONSHIP_OPTIONS } from 'shared/utils/constants'

import { updateIndividual, loadHpoTerms } from 'redux/rootReducer'
import {
  getSamplesByGuid, getMmeSubmissionsByGuid, getHpoTermsByParent, getHpoTermsIsLoading,
} from 'redux/selectors'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'
import {
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED, CASE_REVIEW_STATUS_OPTIONS, CASE_REVIEW_TABLE_NAME, INDIVIDUAL_DETAIL_FIELDS,
  ONSET_AGE_OPTIONS, INHERITANCE_MODE_OPTIONS, INHERITANCE_MODE_LOOKUP, AR_FIELDS,
} from '../../constants'
import { getCurrentProject } from '../../selectors'

import CaseReviewStatusDropdown from './CaseReviewStatusDropdown'


const Detail = styled.div`
  display: inline-block;
  padding: 5px 0 5px 5px;
  font-size: 11px;
  font-weight: 500;
  color: #999999;
`

const CaseReviewDropdownContainer = styled.div`
  float: right;
  width: 220px;
`

const ScrollingTab = styled(Tab).attrs({ menu: { attached: true } })`
  .menu.attached {
    overflow-x: scroll;
  }
  
  .menu.text {
    margin: .1em -.5em;
  }
`

const FLAG_TITLE = {
  chimera: '% Chimera',
  contamination: '% Contamination',
  coverage_exome: '% 20X Coverage',
  coverage_genome: 'Mean Coverage',
}

const POPULATION_MAP = {
  AFR: 'African',
  AMR: 'Latino',
  ASJ: 'Ashkenazi Jewish',
  EAS: 'East Asian',
  FIN: 'European (Finnish)',
  MDE: 'Middle Eastern',
  NFE: 'European (non-Finnish)',
  OTH: 'Other',
  SAS: 'South Asian',
}

const ETHNICITY_OPTIONS = [
  'Aboriginal Australian',
  'African',
  'Arab',
  'Ashkenazi Jewish',
  'Asian',
  'Australian',
  'Caucasian',
  'East Asian',
  'Eastern European',
  'European',
  'Finnish',
  'Gypsy',
  'Hispanic',
  'Indian',
  'Latino/a',
  'Native American',
  'North American',
  'Northern European',
  'Sephardic Jewish',
  'South Asian',
  'Western European',
].map(title => ({ title }))

const ratioLabel = (flag) => {
  const words = snakecaseToTitlecase(flag).split(' ')
  return `Ratio ${words[1]}/${words[2]}`
}

const CaseReviewStatus = React.memo(({ individual }) =>
  <CaseReviewDropdownContainer>
    <CaseReviewStatusDropdown individual={individual} />
    {
      individual.caseReviewStatusLastModifiedDate ? (
        <Detail>
          CHANGED ON {new Date(individual.caseReviewStatusLastModifiedDate).toLocaleDateString()}
          { individual.caseReviewStatusLastModifiedBy && ` BY ${individual.caseReviewStatusLastModifiedBy}` }
        </Detail>
      ) : null
    }
  </CaseReviewDropdownContainer>,
)

CaseReviewStatus.propTypes = {
  individual: PropTypes.object.isRequired,
}

const MmeStatusLabel = React.memo(({ title, dateField, color, individual, mmeSubmission }) =>
  <Link to={`/project/${individual.projectGuid}/family_page/${individual.familyGuid}/matchmaker_exchange`}>
    <VerticalSpacer height={5} />
    <Label color={color} size="small">
      {title}: {new Date(mmeSubmission[dateField]).toLocaleDateString()}
    </Label>
  </Link>,
)

MmeStatusLabel.propTypes = {
  title: PropTypes.string,
  dateField: PropTypes.string,
  color: PropTypes.string,
  individual: PropTypes.object,
  mmeSubmission: PropTypes.object,
}

const DataDetails = React.memo(({ loadedSamples, individual, mmeSubmission }) =>
  <div>
    {loadedSamples.map(sample =>
      <div key={sample.sampleGuid}>
        <Sample loadedSample={sample} isOutdated={!sample.isActive} />
      </div>,
    )}
    {mmeSubmission && (
      mmeSubmission.deletedDate ? (
        <Popup
          flowing
          trigger={
            <MmeStatusLabel title="Removed from MME" dateField="deletedDate" color="red" individual={individual} mmeSubmission={mmeSubmission} />
          }
          content={
            <div>
              <b>Originally Submitted: </b>{new Date(mmeSubmission.createdDate).toLocaleDateString()}
            </div>
          }
        />
      ) : <MmeStatusLabel title="Submitted to MME" dateField="lastModifiedDate" color="violet" individual={individual} mmeSubmission={mmeSubmission} />
    )
  }
  </div>,
)

DataDetails.propTypes = {
  mmeSubmission: PropTypes.object,
  individual: PropTypes.object,
  loadedSamples: PropTypes.array,
}

const formatGene = gene =>
  <span>{gene.gene} {gene.comments ? ` (${gene.comments.trim()})` : ''}</span>

const AgeDetails = ({ birthYear, deathYear }) => {
  if (!!deathYear || deathYear === 0) {
    let deathSummary
    if (deathYear > 0) {
      deathSummary = birthYear > 0 ? `at age ${deathYear - birthYear}` : `in ${deathYear}`
    } else {
      deathSummary = '(date unknown)'
    }
    return (
      <div>
        Deceased {deathSummary}
        {birthYear > 0 && <span> - Born in {birthYear}</span>}
      </div>
    )
  }
  return birthYear > 0 ? new Date().getFullYear() - birthYear : 'Unknown'
}

AgeDetails.propTypes = {
  birthYear: PropTypes.string,
  deathYear: PropTypes.string,
}

const OMIM_CATEGORIES = ['omim']
const GENE_CATEGORIES = ['genes']

const AwesomebarItemSelector = ({ icon, input, ...props }) => {
  const { value, ...fieldProps } = input || props
  return value ? <Input fluid icon={icon} value={value} readOnly /> : <AwesomeBarFormInput {...fieldProps} {...props} />
}

AwesomebarItemSelector.propTypes = {
  input: PropTypes.object,
  icon: PropTypes.node,
  value: PropTypes.oneOf([PropTypes.string, PropTypes.number]),
}

const GeneEntry = ({ name, icon }) =>
  <Form.Group inline>
    <Form.Field width={1}>{icon}</Form.Field>
    <Form.Field width={7}>
      <Field
        name={`${name}.gene`}
        placeholder="Search for gene"
        component={AwesomebarItemSelector}
        categories={GENE_CATEGORIES}
        parseResultItem={result => result.title}
      />
    </Form.Field>
    <Field name={`${name}.comments`} placeholder="Comments" component={Form.Input} width={9} />
  </Form.Group>

GeneEntry.propTypes = {
  icon: PropTypes.node,
  name: PropTypes.string,
}

const getFlattenedHpoTermsByCategory = (features, nonstandardFeatures) =>
  Object.values(getHpoTermsForCategory(
    (features || []).map((term, index) => ({ ...term, index })),
    nonstandardFeatures && nonstandardFeatures.map((term, index) => ({ ...term, index })),
  )).reduce((acc, { categoryName, terms }) => {
    terms[0].categoryName = categoryName
    return [...acc, ...terms]
  }, [])


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

const HpoQualifiers = ({ input }) =>
  <Accordion
    exclusive={false}
    panels={HPO_QUALIFIERS.map(({ type, options }) => ({
      key: type,
      title: { content: <b>{snakecaseToTitlecase(type)}</b> },
      content: {
        content: (
          <RadioGroup
            onChange={val => input.onChange(({ ...input.value, [type]: val }))}
            value={input.value[type]}
            options={options.map(value => ({ value, text: value }))}
            margin="0 1em"
          />
        ),
      },
    }))}
  />

HpoQualifiers.propTypes = {
  input: PropTypes.object,
}

const HpoTermDetails = React.memo(({ value, name, icon, toggleShowDetails, showDetails }) =>
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
        format={val => (val || []).reduce((acc, { type, label }) => ({ ...acc, [type]: label }), {})}
        normalize={val => Object.entries(val || {}).map(([type, label]) => ({ type, label }))}
      />,
      <Form.Group key="notes">
        <Field name={`${name}.notes`} placeholder="Comments" component={Form.Input} width={16} />
      </Form.Group>,
    ]}
  </div>,
)

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

const BaseHpoCategory = ({ category, hpoTerms, addItem, ...props }) =>
  <DataLoader contentId={category} content={hpoTerms} reloadOnIdUpdate {...props}>
    {Object.values(hpoTerms || {}).length > 0 &&
      <Tab.Pane attached={false}>
        {Object.values(hpoTerms).map(term =>
          <Tab key={term.id} menu={CATEGORY_MENU} defaultActiveIndex={null} panes={getTermPanes(term, addItem)} />,
        )}
      </Tab.Pane>
    }
  </DataLoader>

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

const getCategoryPanes = addItem =>
  Object.entries(CATEGORY_NAMES).map(
    ([key, menuItem]) => ({
      key,
      menuItem,
      render: () => <HpoCategory category={key} addItem={addItem} />,
    }),
  ).sort((a, b) => a.menuItem.localeCompare(b.menuItem))

const HpoTermSelector = ({ addItem }) =>
  <div>
    <AwesomeBarFormInput
      parseResultItem={result => ({ id: result.key, label: result.title, category: result.category })}
      categories={HPO_CATEGORIES}
      placeholder="Search for HPO terms"
      onChange={addItem}
    />
    <VerticalSpacer height={10} />
    <ScrollingTab panes={getCategoryPanes(addItem)} defaultActiveIndex={null} />
  </div>

HpoTermSelector.propTypes = {
  addItem: PropTypes.func,
}

class HpoTermsEditor extends React.PureComponent {

  static propTypes = {
    value: PropTypes.array,
    name: PropTypes.string,
    onChange: PropTypes.func,
    header: PropTypes.object,
    allowAdditions: PropTypes.bool,
  }

  state = { showDetails: {}, showAddItem: false }

  toggleShowDetails = id => (e) => {
    e.preventDefault()
    const { showDetails } = this.state
    this.setState({
      showDetails: { ...showDetails, [id]: !showDetails[id] },
    })
  }

  toggleShowAddItems = (e) => {
    e.preventDefault()
    this.setState({
      showAddItem: !this.state.showAddItem,
    })
  }

  addItem = (data) => {
    this.props.onChange([...this.props.value, data])
    this.setState({ showAddItem: false })
  }

  removeItem = (e, data) => {
    e.preventDefault()
    this.props.onChange(this.props.value.filter(({ id }) => id !== data.id))
  }

  render() {
    const { value, name, allowAdditions, header } = this.props
    const { showDetails, showAddItem } = this.state
    return (
      <div>
        {header && <div><Header dividing {...header} /><VerticalSpacer height={5} /></div>}
        {value.map(({ index, ...item }) =>
          <HpoTermDetails
            key={item.id}
            value={item}
            name={`${name}[${index}]`}
            icon={<Icon name="remove" link id={item.id} onClick={this.removeItem} />}
            showDetails={!!showDetails[item.id]}
            toggleShowDetails={this.toggleShowDetails(item.id)}
          />,
        )}
        {allowAdditions && (showAddItem ? <HpoTermSelector addItem={this.addItem} /> :
        <ButtonLink icon="plus" content="Add Feature" onClick={this.toggleShowAddItems} />)}
        {allowAdditions && <VerticalSpacer height={20} />}
      </div>
    )
  }
}

const YEAR_OPTIONS = [{ value: 0, text: 'Unknown' }, ...[...Array(130).keys()].map(i => ({ value: i + 1900 }))]
const YEAR_SELECTOR_PROPS = {
  component: Select,
  options: YEAR_OPTIONS,
  search: true,
  inline: true,
  width: 8,
}

const ETHNICITY_FIELD = {
  component: ListFieldView,
  formFieldProps: {
    control: SearchInput,
    options: ETHNICITY_OPTIONS,
    showNoResults: false,
    fluid: true,
    maxLength: 40,
  },
  itemJoin: ' / ',
}

const GENES_FIELD = {
  component: ListFieldView,
  itemDisplay: formatGene,
  itemKey: ({ gene }) => gene,
  formFieldProps: { itemComponent: GeneEntry },
  individualFields: ({ affected }) => ({
    isVisible: affected === AFFECTED,
  }),
}

const INDIVIDUAL_FIELD_RENDER_LOOKUP = {
  probandRelationship: {
    component: OptionFieldView,
    tagOptions: PROBAND_RELATIONSHIP_OPTIONS,
    formFieldProps: {
      search: true,
    },
  },
  age: {
    subFieldProps: YEAR_SELECTOR_PROPS,
    subFieldsLookup: {
      deathYear: {
        format: val => (val === 0 ? 0 : (val || -1)),
        normalize: val => (val < 0 ? null : val),
        options: [{ value: -1, text: 'Alive' }, ...YEAR_OPTIONS],
      },
    },
    fieldDisplay: AgeDetails,
    individualFields: individual => ({
      fieldValue: individual,
    }),
  },
  onsetAge: {
    component: OptionFieldView,
    tagOptions: ONSET_AGE_OPTIONS,
    formFieldProps: {
      search: true,
    },
    individualFields: ({ affected }) => ({
      isVisible: affected === AFFECTED,
    }),
  },
  notes: {
    component: TextFieldView,
  },
  consanguinity: {
    component: NullableBoolFieldView,
    individualFields: ({ affected }) => ({
      isVisible: affected === AFFECTED,
    }),
  },
  affectedRelatives: {
    component: NullableBoolFieldView,
    individualFields: ({ affected }) => ({
      isVisible: affected === AFFECTED,
    }),
  },
  expectedInheritance: {
    component: TagFieldView,
    tagOptions: INHERITANCE_MODE_OPTIONS,
    simplifiedValue: true,
    fieldDisplay: modes => modes.map(inheritance => INHERITANCE_MODE_LOOKUP[inheritance]).join(', '),
    individualFields: ({ affected }) => ({
      isVisible: affected === AFFECTED,
    }),
  },
  ar: {
    fieldDisplay: individual => Object.keys(AR_FIELDS).filter(
      field => individual[field] || individual[field] === false).map(field =>
        <div key={field}>{individual[field] ? AR_FIELDS[field] : <s>{AR_FIELDS[field]}</s>}</div>,
    ),
    subFieldProps: { margin: '5px 0', radioLabelStyle: 'width: 250px', ...NULLABLE_BOOL_FIELD },
    individualFields: individual => ({
      isVisible: individual.affected === AFFECTED,
      fieldValue: individual,
    }),
  },
  maternalEthnicity: ETHNICITY_FIELD,
  paternalEthnicity: ETHNICITY_FIELD,
  population: {
    fieldDisplay: population => POPULATION_MAP[population] || population,
  },
  filterFlags: {
    fieldDisplay: filterFlags => Object.entries(filterFlags).map(([flag, val]) =>
      <Label
        key={flag}
        basic
        horizontal
        color="orange"
        content={`${FLAG_TITLE[flag] || snakecaseToTitlecase(flag)}: ${parseFloat(val).toFixed(2)}`}
      />,
    ),
  },
  popPlatformFilters: {
    fieldDisplay: filterFlags => Object.keys(filterFlags).map(flag =>
      <Label
        key={flag}
        basic
        horizontal
        color="orange"
        content={flag.startsWith('r_') ? ratioLabel(flag) : snakecaseToTitlecase(flag.replace('n_', 'num._'))}
      />,
    ),
  },
  svFlags: {
    fieldDisplay: filterFlags => filterFlags.map(flag =>
      <Label
        key={flag}
        basic
        horizontal
        color="orange"
        content={snakecaseToTitlecase(flag)}
      />,
    ),
  },
  features: {
    fieldDisplay: individual => <HpoPanel individual={individual} />,
    formFields: [
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
    ],
    individualFields: individual => ({
      initialValues: { ...individual, individualField: 'hpo_terms' },
      fieldValue: individual,
    }),
  },
  disorders: {
    component: ListFieldView,
    formFieldProps: {
      itemComponent: AwesomebarItemSelector,
      placeholder: 'Search for OMIM disorder',
      categories: OMIM_CATEGORIES,
    },
    itemDisplay: mim => <a target="_blank" href={`https://www.omim.org/entry/${mim}`}>{mim}</a>,
    individualFields: ({ affected }) => ({
      isVisible: affected === AFFECTED,
    }),
  },
  rejectedGenes: GENES_FIELD,
  candidateGenes: GENES_FIELD,
}

const INDIVIDUAL_FIELDS = INDIVIDUAL_DETAIL_FIELDS.map(({ field, header, subFields, isEditable, isPrivate }) => {
  const { subFieldsLookup, subFieldProps, ...fieldProps } = INDIVIDUAL_FIELD_RENDER_LOOKUP[field]
  const formattedField = { field, fieldName: header, isEditable, isPrivate, ...fieldProps }
  if (subFields) {
    formattedField.formFields = subFields.map(subField => (
      { name: subField.field, label: subField.header, ...subFieldProps, ...(subFieldsLookup || {})[subField.field] }
    ))
  }
  return formattedField
})

const CASE_REVIEW_FIELDS = [
  {
    component: TextFieldView,
    fieldName: 'Case Review Discussion',
    field: 'caseReviewDiscussion',
    isEditable: true,
    individualFields: ({ caseReviewStatus, caseReviewDiscussion }) => ({
      isVisible: caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED || caseReviewDiscussion,
      individualField: 'case_review_discussion',
    }),
  },
  ...INDIVIDUAL_FIELDS,
]

const NON_CASE_REVIEW_FIELDS = [
  {
    component: OptionFieldView,
    fieldName: 'Case Review Status',
    field: 'caseReviewStatus',
    tagOptions: CASE_REVIEW_STATUS_OPTIONS,
    tagAnnotation: value => <ColoredIcon name="stop" color={value.color} />,
  },
  {
    component: TextFieldView,
    fieldName: 'Discussion',
    field: 'caseReviewDiscussion',
    individualFields: ({ caseReviewStatus }) => ({
      isVisible: caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED,
    }),
  },
  ...INDIVIDUAL_FIELDS,
]

const IndividualRow = React.memo((
  { project, family, individual, mmeSubmission, samplesByGuid, dispatchUpdateIndividual, tableName },
) => {
  const { displayName, paternalId, maternalId, sex, affected, createdDate, sampleGuids } = individual

  let loadedSamples = sampleGuids.map(
    sampleGuid => samplesByGuid[sampleGuid],
  )
  loadedSamples = orderBy(loadedSamples, [s => s.loadedDate], 'desc')
  // only show active or first/ last inactive samples
  loadedSamples = loadedSamples.filter((sample, i) => sample.isActive || i === 0 || i === loadedSamples.length - 1)

  const leftContent =
    <div>
      <div>
        <PedigreeIcon sex={sex} affected={affected} /> {displayName}
      </div>
      <div>
        {
          (!family.pedigreeImage && ((paternalId && paternalId !== '.') || (maternalId && maternalId !== '.'))) ? (
            <Detail>
              child of &nbsp;
              <i>{(paternalId && maternalId) ? `${paternalId} and ${maternalId}` : (paternalId || maternalId) }</i>
              <br />
            </Detail>
          ) : null
        }
        <Detail>
          ADDED {new Date(createdDate).toLocaleDateString().toUpperCase()}
        </Detail>
      </div>
    </div>

  const editCaseReview = tableName === CASE_REVIEW_TABLE_NAME
  const rightContent = editCaseReview ?
    <CaseReviewStatus individual={individual} /> :
    <DataDetails loadedSamples={loadedSamples} individual={individual} mmeSubmission={mmeSubmission} />

  const fields = editCaseReview ? CASE_REVIEW_FIELDS : NON_CASE_REVIEW_FIELDS

  return (
    <FamilyLayout
      fields={fields}
      fieldDisplay={({ component, isEditable, onSubmit, individualFields = () => {}, ...field }) =>
        React.createElement(component || BaseFieldView, {
          key: field.field,
          isEditable: isEditable && project.canEdit,
          onSubmit: isEditable && dispatchUpdateIndividual,
          modalTitle: isEditable && `${field.fieldName} for Individual ${displayName}`,
          initialValues: individual,
          idField: 'individualGuid',
          ...individualFields(individual),
          ...field,
        })
      }
      leftContent={leftContent}
      rightContent={rightContent}
    />
  )
})

IndividualRow.propTypes = {
  project: PropTypes.object.isRequired,
  family: PropTypes.object.isRequired,
  individual: PropTypes.object.isRequired,
  mmeSubmission: PropTypes.object,
  samplesByGuid: PropTypes.object.isRequired,
  dispatchUpdateIndividual: PropTypes.func,
  tableName: PropTypes.string,
}

export { IndividualRow as IndividualRowComponent }

const mapStateToProps = (state, ownProps) => ({
  project: getCurrentProject(state),
  samplesByGuid: getSamplesByGuid(state),
  mmeSubmission: getMmeSubmissionsByGuid(state)[ownProps.individual.mmeSubmissionGuid],
})


const mapDispatchToProps = {
  dispatchUpdateIndividual: updateIndividual,
}

export default connect(mapStateToProps, mapDispatchToProps)(IndividualRow)
