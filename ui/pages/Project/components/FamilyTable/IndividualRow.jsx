import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Field } from 'react-final-form'
import { Label, Popup, Form, Input, Loader } from 'semantic-ui-react'
import orderBy from 'lodash/orderBy'

import { SearchInput, YearSelector, RadioButtonGroup, ButtonRadioGroup, Select } from 'shared/components/form/Inputs'
import PedigreeIcon from 'shared/components/icons/PedigreeIcon'
import Modal from 'shared/components/modal/Modal'
import { AwesomeBarFormInput } from 'shared/components/page/AwesomeBar'
import BaseFieldView from 'shared/components/panel/view-fields/BaseFieldView'
import TagFieldView from 'shared/components/panel/view-fields/TagFieldView'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import ListFieldView from 'shared/components/panel/view-fields/ListFieldView'
import NullableBoolFieldView, { NULLABLE_BOOL_FIELD } from 'shared/components/panel/view-fields/NullableBoolFieldView'
import OptionFieldView from 'shared/components/panel/view-fields/OptionFieldView'
import Sample from 'shared/components/panel/sample'
import FamilyLayout from 'shared/components/panel/family/FamilyLayout'
import { ColoredIcon, ButtonLink } from 'shared/components/StyledComponents'
import { VerticalSpacer } from 'shared/components/Spacers'
import {
  AFFECTED, PROBAND_RELATIONSHIP_OPTIONS, SAMPLE_TYPE_RNA, INDIVIDUAL_FIELD_CONFIGS, INDIVIDUAL_FIELD_SEX,
  INDIVIDUAL_FIELD_AFFECTED, INDIVIDUAL_FIELD_FEATURES, INDIVIDUAL_FIELD_LOOKUP,
} from 'shared/utils/constants'

import { updateIndividual } from 'redux/rootReducer'
import { getSamplesByGuid, getMmeSubmissionsByGuid } from 'redux/selectors'
import { HPO_FORM_FIELDS } from '../HpoTerms'
import {
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED, CASE_REVIEW_STATUS_OPTIONS, CASE_REVIEW_TABLE_NAME, INDIVIDUAL_DETAIL_FIELDS,
  ONSET_AGE_OPTIONS, INHERITANCE_MODE_OPTIONS, INHERITANCE_MODE_LOOKUP, AR_FIELDS,
} from '../../constants'
import { updateIndividuals } from '../../reducers'
import { getCurrentProject, getParentOptionsByIndividual } from '../../selectors'

import CaseReviewStatusDropdown from './CaseReviewStatusDropdown'
import CollapsableLayout from './CollapsableLayout'

const PhenotypePrioritizedGenes = React.lazy(() => import('../PhenotypePrioritizedGenes'))

const Detail = styled.div`
  display: inline-block;
  padding: 5px 0 5px 5px;
  font-size: 11px;
  font-weight: 500;
  color: #999999;
`

const CaseReviewDropdownContainer = styled.div`
  float: right;
  width: 100%;
`

const IndividualContainer = styled.div`
 display: inline-block;
`

const PaddedRadioButtonGroup = styled(RadioButtonGroup)`
  padding: 10px;
`

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

const CaseReviewStatus = React.memo(({ individual }) => (
  <CaseReviewDropdownContainer>
    <CaseReviewStatusDropdown individual={individual} />
    {
      individual.caseReviewStatusLastModifiedDate ? (
        <Detail>
          {`CHANGED ON ${new Date(individual.caseReviewStatusLastModifiedDate).toLocaleDateString()}
          ${individual.caseReviewStatusLastModifiedBy && ` BY ${individual.caseReviewStatusLastModifiedBy}`}`}
        </Detail>
      ) : null
    }
  </CaseReviewDropdownContainer>
))

CaseReviewStatus.propTypes = {
  individual: PropTypes.object.isRequired,
}

const SHOW_DATA_MODAL_CONFIG = [
  {
    shouldShowField: 'hasPhenotypeGeneScores',
    component: PhenotypePrioritizedGenes,
    modalName: ({ individualId }) => `PHENOTYPE-PRIORITIZATION-${individualId}`,
    title: ({ individualId }) => `Phenotype Prioritized Genes: ${individualId}`,
    modalSize: 'large',
    linkText: 'Show Phenotype Prioritized Genes',
  },
]

const MmeStatusLabel = React.memo(({ title, dateField, color, individual, mmeSubmission }) => (
  <Link to={`/project/${individual.projectGuid}/family_page/${individual.familyGuid}/matchmaker_exchange`}>
    <VerticalSpacer height={5} />
    <Label color={color} size="small">
      {`${title}: ${new Date(mmeSubmission[dateField]).toLocaleDateString()}`}
    </Label>
  </Link>
))

MmeStatusLabel.propTypes = {
  title: PropTypes.string,
  dateField: PropTypes.string,
  color: PropTypes.string,
  individual: PropTypes.object,
  mmeSubmission: PropTypes.object,
}

const DataDetails = React.memo(({ loadedSamples, individual, mmeSubmission }) => (
  <div>
    {loadedSamples.map(
      sample => <div key={sample.sampleGuid}><Sample loadedSample={sample} isOutdated={!sample.isActive} /></div>,
    )}
    {mmeSubmission && (
      mmeSubmission.deletedDate ? (
        <Popup
          flowing
          trigger={
            <div>
              <MmeStatusLabel title="Removed from MME" dateField="deletedDate" color="red" individual={individual} mmeSubmission={mmeSubmission} />
            </div>
          }
          content={
            <div>
              <b>Originally Submitted: </b>
              {new Date(mmeSubmission.createdDate).toLocaleDateString()}
            </div>
          }
        />
      ) : <MmeStatusLabel title="Submitted to MME" dateField="lastModifiedDate" color="violet" individual={individual} mmeSubmission={mmeSubmission} />
    )}
    {individual.hasRnaOutlierData && (
      <div>
        <Link
          target="_blank"
          to={`/project/${individual.projectGuid}/family_page/${individual.familyGuid}/rnaseq_results/${individual.individualGuid}`}
        >
          RNAseq Results
        </Link>
      </div>
    )}
    {SHOW_DATA_MODAL_CONFIG.filter(({ shouldShowField }) => individual[shouldShowField]).map(
      ({ modalName, title, modalSize, linkText, component }) => {
        const sample = loadedSamples.find(({ sampleType, isActive }) => isActive && sampleType === SAMPLE_TYPE_RNA)
        const titleIds = { sampleId: sample?.sampleId, individualId: individual.individualId }
        return (
          <Modal
            key={modalName(titleIds)}
            modalName={modalName(titleIds)}
            title={title(titleIds)}
            size={modalSize}
            trigger={<ButtonLink padding="0 0 0 0" content={linkText} />}
          >
            <React.Suspense fallback={<Loader />}>
              {React.createElement(component,
                { familyGuid: individual.familyGuid, individualGuid: individual.individualGuid }) }
            </React.Suspense>
          </Modal>
        )
      },
    )}
  </div>
))

DataDetails.propTypes = {
  mmeSubmission: PropTypes.object,
  individual: PropTypes.object,
  loadedSamples: PropTypes.arrayOf(PropTypes.object),
}

const formatGene = gene => `${gene.gene} ${gene.comments ? ` (${gene.comments.trim()})` : ''}`

const AgeDetails = ({ birthYear, deathYear }) => {
  if (!!deathYear || deathYear === 0) {
    let deathSummary
    if (deathYear > 0) {
      deathSummary = birthYear > 0 ? `at age ${deathYear - birthYear}` : `in ${deathYear}`
    } else {
      deathSummary = '(date unknown)'
    }
    return <div>{`Deceased ${deathSummary}${birthYear > 0 ? ` - Born in ${birthYear}` : ''}`}</div>
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

const getResultTitle = result => result.title

const GeneEntry = ({ name, icon }) => (
  <Form.Group inline>
    <Form.Field width={1}>{icon}</Form.Field>
    <Form.Field width={7}>
      <Field
        name={`${name}.gene`}
        placeholder="Search for gene"
        component={AwesomebarItemSelector}
        categories={GENE_CATEGORIES}
        parseResultItem={getResultTitle}
      />
    </Form.Field>
    <Field name={`${name}.comments`} placeholder="Comments" component={Form.Input} width={9} />
  </Form.Group>
)

GeneEntry.propTypes = {
  icon: PropTypes.node,
  name: PropTypes.string,
}

const YEAR_SELECTOR_PROPS = {
  component: YearSelector,
  includeUnknown: true,
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
        parse: val => (val < 0 ? null : val),
        includeAlive: true,
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
      field => individual[field] || individual[field] === false,
    ).map(field => <div key={field}>{individual[field] ? AR_FIELDS[field] : <s>{AR_FIELDS[field]}</s>}</div>),
    subFieldProps: {
      margin: '5px 0',
      groupContainer: props => <RadioButtonGroup radioLabelStyle="width: 250px" {...props} />,
      ...NULLABLE_BOOL_FIELD,
    },
    individualFields: individual => ({
      isVisible: individual.affected === AFFECTED,
      fieldValue: individual,
    }),
  },
  maternalEthnicity: ETHNICITY_FIELD,
  paternalEthnicity: ETHNICITY_FIELD,
  population: {
    fieldDisplay: population => POPULATION_MAP[population] || population || 'Not Loaded',
  },
  [INDIVIDUAL_FIELD_FEATURES]: { formFields: HPO_FORM_FIELDS },
  disorders: {
    component: ListFieldView,
    formFieldProps: {
      itemComponent: AwesomebarItemSelector,
      placeholder: 'Search for OMIM disorder',
      categories: OMIM_CATEGORIES,
    },
    itemDisplay: mim => <a target="_blank" rel="noreferrer" href={`https://www.omim.org/entry/${mim}`}>{mim}</a>,
    individualFields: ({ affected }) => ({
      isVisible: affected === AFFECTED,
    }),
  },
  rejectedGenes: GENES_FIELD,
  candidateGenes: GENES_FIELD,
}

const INDIVIDUAL_FIELDS = INDIVIDUAL_DETAIL_FIELDS.map(
  ({ field, header, subFields, isEditable, isCollaboratorEditable, isRequiredInternal, isPrivate }) => {
    const { subFieldsLookup, subFieldProps, ...fieldProps } = INDIVIDUAL_FIELD_RENDER_LOOKUP[field] || {}
    const coreField = {
      field, fieldName: header, isEditable, isCollaboratorEditable, isRequiredInternal, isPrivate,
    }
    const formattedField = { ...(INDIVIDUAL_FIELD_LOOKUP[field] || {}), ...coreField, ...fieldProps }
    if (subFields) {
      formattedField.formFields = subFields.map(subField => (
        { name: subField.field, label: subField.header, ...subFieldProps, ...(subFieldsLookup || {})[subField.field] }
      ))
    }
    return formattedField
  },
)

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
  {
    field: 'analyteType',
    fieldName: 'Analyte Type',
    isEditable: true,
    isPrivate: true,
    component: OptionFieldView,
    tagOptions: [
      { value: 'D', text: 'DNA' },
      { value: 'R', text: 'RNA' },
      { value: 'B', text: 'blood plasma' },
      { value: 'F', text: 'frozen whole blood' },
      { value: 'H', text: 'high molecular weight DNA' },
      { value: 'U', text: 'urine' },
    ],
  },
  {
    field: 'primaryBiosample',
    fieldName: 'Primary Biosample',
    isEditable: true,
    isPrivate: true,
    component: OptionFieldView,
    tagOptions: [
      { value: 'T', text: 'UBERON:0000479 (tissue)' },
      { value: 'NT', text: 'UBERON:0003714 (neural tissue)' },
      { value: 'S', text: 'UBERON:0001836 (saliva)' },
      { value: 'SE', text: 'UBERON:0001003 (skin epidermis)' },
      { value: 'MT', text: 'UBERON:0002385 (muscle tissue)' },
      { value: 'WB', text: 'UBERON:0000178 (whole blood)' },
      { value: 'BM', text: 'UBERON:0002371 (bone marrow)' },
      { value: 'CC', text: 'UBERON:0006956 (buccal mucosa)' },
      { value: 'CF', text: 'UBERON:0001359 (cerebrospinal fluid)' },
      { value: 'U', text: 'UBERON:0001088 (urine)' },
      { value: 'NE', text: 'UBERON:0019306 (nose epithelium)' },
    ],
  },
  {
    field: 'tissueAffectedStatus',
    fieldName: 'Tissue Affected Status',
    isEditable: true,
    isPrivate: true,
    component: NullableBoolFieldView,
  },
  ...INDIVIDUAL_FIELDS,
]
const EMPTY_FIELDS = [{ id: 'blank', colWidth: 10, component: () => null }]

const mapParentOptionsStateToProps = (state, ownProps) => {
  const options = getParentOptionsByIndividual(state)[ownProps.meta.data.formId][ownProps.sex] || []
  return options.length > 0 ? { options: [{ value: null, text: 'None' }, ...options] } : { options, disabled: true }
}

const EDIT_INDIVIDUAL_FIELDS = [INDIVIDUAL_FIELD_SEX, INDIVIDUAL_FIELD_AFFECTED].map((name) => {
  const { label, formFieldProps = {} } = INDIVIDUAL_FIELD_CONFIGS[name]
  return { name, label, ...formFieldProps, component: ButtonRadioGroup, groupContainer: PaddedRadioButtonGroup }
}).concat([
  { name: 'paternalGuid', label: 'Father', sex: 'M' }, { name: 'maternalGuid', label: 'Mother', sex: 'F' },
].map(field => (
  { ...field, component: connect(mapParentOptionsStateToProps)(Select), inline: true, width: 8 }
)))

class IndividualRow extends React.PureComponent {

  static propTypes = {
    project: PropTypes.object.isRequired,
    individual: PropTypes.object.isRequired,
    mmeSubmission: PropTypes.object,
    samplesByGuid: PropTypes.object.isRequired,
    dispatchUpdateIndividual: PropTypes.func,
    updateIndividualPedigree: PropTypes.func,
    tableName: PropTypes.string,
  }

  individualFieldDisplay = ({
    component, isEditable, isCollaboratorEditable, isRequiredInternal, onSubmit, individualFields = () => {}, ...field
  }) => {
    const { project, individual, dispatchUpdateIndividual } = this.props
    return React.createElement(component || BaseFieldView, {
      key: field.field,
      isEditable: isCollaboratorEditable || (isEditable && project.canEdit),
      isRequired: isRequiredInternal && individual.affected === AFFECTED && project.isAnalystProject,
      onSubmit: (isEditable || isCollaboratorEditable) && dispatchUpdateIndividual,
      modalTitle: (isEditable || isCollaboratorEditable) && `${field.fieldName} for Individual ${individual.displayName}`,
      initialValues: individual,
      idField: 'individualGuid',
      ...individualFields(individual),
      ...field,
    })
  }

  render() {
    const { project, individual, mmeSubmission, samplesByGuid, tableName, updateIndividualPedigree } = this.props
    const { displayName, sex, affected, createdDate, sampleGuids } = individual

    let loadedSamples = sampleGuids.map(
      sampleGuid => samplesByGuid[sampleGuid],
    )
    loadedSamples = orderBy(loadedSamples, [s => s.loadedDate], 'desc')
    // only show active or first/ last inactive samples
    loadedSamples = loadedSamples.filter((sample, i) => sample.isActive || i === 0 || i === loadedSamples.length - 1)

    const leftContent = (
      <IndividualContainer>
        <div>
          <PedigreeIcon sex={sex} affected={affected} />
          {displayName}
        </div>
        <div>
          <Detail>
            {`ADDED ${new Date(createdDate).toLocaleDateString().toUpperCase()}`}
          </Detail>
        </div>
        <BaseFieldView
          field="coreEdit"
          idField="individualGuid"
          initialValues={individual}
          isEditable={!!project.workspaceName && !project.isAnalystProject && project.canEdit}
          isDeletable
          deleteConfirm={`Are you sure you want to delete ${displayName}? This action can not be undone`}
          editLabel="Edit Individual"
          formFields={EDIT_INDIVIDUAL_FIELDS}
          modalTitle={`Edit ${displayName}`}
          showErrorPanel
          onSubmit={updateIndividualPedigree}
        />
      </IndividualContainer>
    )

    const editCaseReview = tableName === CASE_REVIEW_TABLE_NAME
    const rightContent = editCaseReview ?
      <CaseReviewStatus individual={individual} /> :
      <DataDetails loadedSamples={loadedSamples} individual={individual} mmeSubmission={mmeSubmission} />

    return (
      <CollapsableLayout
        layoutComponent={FamilyLayout}
        detailFields={editCaseReview ? CASE_REVIEW_FIELDS : NON_CASE_REVIEW_FIELDS}
        noDetailFields={editCaseReview ? EMPTY_FIELDS : null}
        fieldDisplay={this.individualFieldDisplay}
        leftContent={leftContent}
        rightContent={rightContent}
      />
    )
  }

}

export { IndividualRow as IndividualRowComponent }

const mapStateToProps = (state, ownProps) => ({
  project: getCurrentProject(state),
  samplesByGuid: getSamplesByGuid(state),
  mmeSubmission: getMmeSubmissionsByGuid(state)[ownProps.individual.mmeSubmissionGuid],
})

const mapDispatchToProps = {
  dispatchUpdateIndividual: updateIndividual,
  updateIndividualPedigree: values => updateIndividuals({ individuals: [values], delete: values.delete }),
}

export default connect(mapStateToProps, mapDispatchToProps)(IndividualRow)
