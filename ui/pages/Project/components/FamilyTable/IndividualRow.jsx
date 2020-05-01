import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Field } from 'redux-form'
import { Label, Popup, Form, Input } from 'semantic-ui-react'
import orderBy from 'lodash/orderBy'

import { Select, SearchInput } from 'shared/components/form/Inputs'
import PedigreeIcon from 'shared/components/icons/PedigreeIcon'
import { AwesomeBarFormInput } from 'shared/components/page/AwesomeBar'
import BaseFieldView from 'shared/components/panel/view-fields/BaseFieldView'
import TagFieldView from 'shared/components/panel/view-fields/TagFieldView'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import ListFieldView from 'shared/components/panel/view-fields/ListFieldView'
import NullableBoolFieldView, { getNullableBoolField } from 'shared/components/panel/view-fields/NullableBoolFieldView'
import OptionFieldView from 'shared/components/panel/view-fields/OptionFieldView'
import HpoPanel from 'shared/components/panel/HpoPanel'
import Sample from 'shared/components/panel/sample'
import { FamilyLayout } from 'shared/components/panel/family'
import { ColoredIcon } from 'shared/components/StyledComponents'
import { VerticalSpacer } from 'shared/components/Spacers'
import { AFFECTED } from 'shared/utils/constants'

import { updateIndividual } from 'redux/rootReducer'
import { getSamplesByGuid, getCurrentProject, getMmeSubmissionsByGuid } from 'redux/selectors'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'
import { CASE_REVIEW_STATUS_MORE_INFO_NEEDED, CASE_REVIEW_STATUS_OPTIONS } from '../../constants'

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

const ONSET_AGE_OPTIONS = [
  { value: 'G', text: 'Congenital onset' },
  { value: 'E', text: 'Embryonal onset' },
  { value: 'F', text: 'Fetal onset' },
  { value: 'N', text: 'Neonatal onset' },
  { value: 'I', text: 'Infantile onset' },
  { value: 'C', text: 'Childhood onset' },
  { value: 'J', text: 'Juvenile onset' },
  { value: 'A', text: 'Adult onset' },
  { value: 'Y', text: 'Young adult onset' },
  { value: 'M', text: 'Middle age onset' },
  { value: 'L', text: 'Late onset' },
]

const INHERITANCE_MODE_OPTIONS = [
  { value: 'S', text: 'Sporadic' },
  { value: 'D', text: 'Autosomal dominant inheritance' },
  { value: 'L', text: 'Sex-limited autosomal dominant' },
  { value: 'A', text: 'Male-limited autosomal dominant' },
  { value: 'C', text: 'Autosomal dominant contiguous gene syndrome' },
  { value: 'R', text: 'Autosomal recessive inheritance' },
  { value: 'G', text: 'Gonosomal inheritance' },
  { value: 'X', text: 'X-linked inheritance' },
  { value: 'Z', text: 'X-linked recessive inheritance' },
  { value: 'Y', text: 'Y-linked inheritance' },
  { value: 'W', text: 'X-linked dominant inheritance' },
  { value: 'F', text: 'Multifactorial inheritance' },
  { value: 'M', text: 'Mitochondrial inheritance' },
]
const INHERITANCE_MODE_MAP = INHERITANCE_MODE_OPTIONS.reduce((acc, { text, value }) => ({ ...acc, [value]: text }), {})

const AR_FIELDS = {
  arFertilityMeds: 'Fertility medications',
  arIui: 'Intrauterine insemination',
  arIvf: 'In vitro fertilization',
  arIcsi: 'Intra-cytoplasmic sperm injection',
  arSurrogacy: 'Gestational surrogacy',
  arDonoregg: 'Donor egg',
  arDonorsperm: 'Donor sperm',
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
  value: PropTypes.oneOf(PropTypes.string, PropTypes.number),
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
  isEditable: true,
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
  isEditable: true,
  itemDisplay: formatGene,
  itemKey: ({ gene }) => gene,
  formFieldProps: { itemComponent: GeneEntry },
  individualFields: ({ affected }) => ({
    isVisible: affected === AFFECTED,
  }),
}

const ShowPhenotipsModalButton = () => 'PHENOTIPS'

const INDIVIDUAL_FIELDS = [
  {
    field: 'age',
    fieldName: 'Age',
    isEditable: true,
    formFields: [
      { name: 'birthYear', label: 'Birth Year', ...YEAR_SELECTOR_PROPS },
      {
        name: 'deathYear',
        label: 'Death Year',
        format: val => (val === 0 ? 0 : (val || -1)),
        normalize: val => (val < 0 ? null : val),
        ...YEAR_SELECTOR_PROPS,
        options: [{ value: -1, text: 'Alive' }, ...YEAR_OPTIONS],
      },
    ],
    fieldDisplay: AgeDetails,
    individualFields: individual => ({
      fieldValue: individual,
    }),
  },
  {
    component: OptionFieldView,
    field: 'onsetAge',
    fieldName: 'Age of Onset',
    isEditable: true,
    tagOptions: ONSET_AGE_OPTIONS,
    formFieldProps: {
      search: true,
    },
    individualFields: ({ affected }) => ({
      isVisible: affected === AFFECTED,
    }),
  },
  {
    component: TextFieldView,
    isEditable: true,
    fieldName: 'Individual Notes',
    field: 'notes',
  },
  {
    component: NullableBoolFieldView,
    field: 'consanguinity',
    fieldName: 'Consanguinity',
    isEditable: true,
    individualFields: ({ affected }) => ({
      isVisible: affected === AFFECTED,
    }),
  },
  {
    component: NullableBoolFieldView,
    field: 'affectedRelatives',
    fieldName: 'Other Affected Relatives',
    isEditable: true,
    individualFields: ({ affected }) => ({
      isVisible: affected === AFFECTED,
    }),
  },
  {
    component: TagFieldView,
    field: 'expectedInheritance',
    fieldName: 'Expected Mode of Inheritance',
    isEditable: true,
    tagOptions: INHERITANCE_MODE_OPTIONS,
    simplifiedValue: true,
    fieldDisplay: modes => modes.map(inheritance => INHERITANCE_MODE_MAP[inheritance]).join(', '),
    individualFields: ({ affected }) => ({
      isVisible: affected === AFFECTED,
    }),
  },
  {
    field: 'ar',
    fieldName: 'Assisted Reproduction',
    isEditable: true,
    fieldDisplay: individual => Object.keys(AR_FIELDS).filter(
      field => individual[field] || individual[field] === false).map(field =>
        <div>{individual[field] ? AR_FIELDS[field] : <s>{AR_FIELDS[field]}</s>}</div>,
    ),
    formFields: Object.entries(AR_FIELDS).map(([field, label]) => ({
      margin: '0 100px 10px 0',
      ...getNullableBoolField({ field, label }),
    })),
    individualFields: individual => ({
      isVisible: individual.affected === AFFECTED,
      fieldValue: individual,
    }),
  },
  {
    field: 'maternalEthnicity',
    fieldName: 'Maternal Ancestry',
    ...ETHNICITY_FIELD,
  },
  {
    field: 'paternalEthnicity',
    fieldName: 'Paternal Ancestry',
    ...ETHNICITY_FIELD,
  },
  {
    fieldName: 'Imputed Population',
    field: 'population',
    fieldDisplay: population => POPULATION_MAP[population] || population,
  },
  {
    fieldName: 'Sample QC Flags',
    field: 'filterFlags',
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
  {
    fieldName: 'Population/Platform Specific Sample QC Flags',
    field: 'popPlatformFilters',
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
  {
    field: 'features',
    fieldName: 'Features',
    isEditable: true,
    editButton: (modalId, initialValues) =>
      <ShowPhenotipsModalButton individual={initialValues} isViewOnly={false} modalId={modalId} />,
    fieldDisplay: individual => <HpoPanel individual={individual} />,
    individualFields: individual => ({
      fieldValue: individual,
    }),
  },
  {
    component: ListFieldView,
    field: 'disorders',
    fieldName: 'Pre-discovery OMIM disorders',
    isEditable: true,
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
  {
    field: 'rejectedGenes',
    fieldName: 'Previously Tested Genes',
    ...GENES_FIELD,
  },
  {
    field: 'candidateGenes',
    fieldName: 'Candidate Genes',
    ...GENES_FIELD,
  },
]

const CASE_REVIEW_FIELDS = [
  {
    component: TextFieldView,
    fieldName: 'Case Review Discussion',
    field: 'caseReviewDiscussion',
    isEditable: true,
    individualFields: ({ caseReviewStatus, caseReviewDiscussion }) => ({
      isVisible: caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED || caseReviewDiscussion,
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
  { project, family, individual, editCaseReview, mmeSubmission, samplesByGuid, dispatchUpdateIndividual },
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
  editCaseReview: PropTypes.bool,
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
