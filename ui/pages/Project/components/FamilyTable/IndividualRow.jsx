import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Field } from 'react-final-form'
import { Label, Popup, Form, Input, Loader } from 'semantic-ui-react'
import orderBy from 'lodash/orderBy'

import { SearchInput, YearSelector, RadioButtonGroup, ButtonRadioGroup, Select } from 'shared/components/form/Inputs'
import { validators } from 'shared/components/form/FormHelpers'
import LoadOptionsSelect from 'shared/components/form/LoadOptionsSelect'
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
  AFFECTED, PROBAND_RELATIONSHIP_OPTIONS, INDIVIDUAL_FIELD_CONFIGS, INDIVIDUAL_FIELD_SEX,
  INDIVIDUAL_FIELD_AFFECTED, INDIVIDUAL_FIELD_FEATURES, INDIVIDUAL_FIELD_LOOKUP, DATASET_TITLE_LOOKUP,
  DATA_TYPE_EXPRESSION_OUTLIER, DATA_TYPE_SPLICE_OUTLIER, INDIVIDUAL_FIELD_ANALYTE_TYPE,
  INDIVIDUAL_FIELD_TISSUE_AFFECTED, INDIVIDUAL_FIELD_PRIMARY_BIOSAMPLE,
} from 'shared/utils/constants'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'

import { updateIndividual } from 'redux/rootReducer'
import { getSamplesByGuid, getMmeSubmissionsByGuid, getIGVSamplesByFamilySampleIndividual } from 'redux/selectors'
import { HPO_FORM_FIELDS } from '../HpoTerms'
import {
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED, CASE_REVIEW_STATUS_OPTIONS, CASE_REVIEW_TABLE_NAME, INDIVIDUAL_DETAIL_FIELDS,
  ONSET_AGE_OPTIONS, INHERITANCE_MODE_OPTIONS, INHERITANCE_MODE_LOOKUP, AR_FIELDS,
} from '../../constants'
import { updateIndividuals, updateIndividualIGV } from '../../reducers'
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
  
  .button {
    padding-left: 1em !important;
    padding-right: 1em !important;
    
    &.labeled .label {
      margin-left: 0px !important;
    }
  }
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
  AmInd: 'American Indian',
  PaIsl: 'Pacific Islander',
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
      sample => <div key={sample.sampleGuid}><Sample {...sample} isOutdated={!sample.isActive} /></div>,
    )}
    {individual.rnaSample && (
      <Sample
        sampleType="RNA"
        loadedDate={individual.rnaSample.loadedDate}
        hoverContent={`RNAseq methods: ${individual.rnaSample.dataTypes.map(dt => DATASET_TITLE_LOOKUP[dt].trim()).join(', ')}`}
      />
    )}
    {individual.rnaSample && (individual.rnaSample.dataTypes.includes(DATA_TYPE_EXPRESSION_OUTLIER) ||
      individual.rnaSample.dataTypes.includes(DATA_TYPE_SPLICE_OUTLIER)) && (
      <div>
        <Link
          target="_blank"
          to={`/project/${individual.projectGuid}/family_page/${individual.familyGuid}/rnaseq_results/${individual.individualGuid}`}
        >
          RNAseq Results
        </Link>
      </div>
    )}
    {individual.phenotypePrioritizationTools.map(
      ({ tool, loadedDate }) => (
        <div key={tool}><Sample sampleType={snakecaseToTitlecase(tool)} loadedDate={loadedDate} /></div>
      ),
    )}
    {individual.phenotypePrioritizationTools.length > 0 && (
      <Modal
        modalName={`PHENOTYPE-PRIORITIZATION-${individual.individualId}`}
        title={`Phenotype Prioritized Genes: ${individual.individualId}`}
        size="large"
        trigger={<ButtonLink padding="0 0 0 0" content="Show Phenotype Prioritized Genes" />}
      >
        <React.Suspense fallback={<Loader />}>
          <PhenotypePrioritizedGenes familyGuid={individual.familyGuid} individualGuid={individual.individualGuid} />
        </React.Suspense>
      </Modal>
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

const INDIVIDUAL_FIELD_CONFIG_SEX = INDIVIDUAL_FIELD_CONFIGS[INDIVIDUAL_FIELD_SEX]

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
    field: INDIVIDUAL_FIELD_SEX,
    fieldName: INDIVIDUAL_FIELD_CONFIG_SEX.label,
    isEditable: false,
    component: OptionFieldView,
    tagOptions: INDIVIDUAL_FIELD_CONFIG_SEX.formFieldProps.options,
  },
  ...[
    INDIVIDUAL_FIELD_ANALYTE_TYPE,
    INDIVIDUAL_FIELD_PRIMARY_BIOSAMPLE,
    INDIVIDUAL_FIELD_TISSUE_AFFECTED,
  ].map((field) => {
    const { label, formFieldProps = {} } = INDIVIDUAL_FIELD_CONFIGS[field]
    return {
      field,
      fieldName: label,
      isEditable: true,
      isPrivate: true,
      component: formFieldProps.options ? OptionFieldView : NullableBoolFieldView,
      tagOptions: formFieldProps.options,
    }
  }),
  {
    field: 'solveStatus',
    fieldName: 'Participant Solve Status',
    isEditable: true,
    isPrivate: true,
    component: OptionFieldView,
    tagOptions: [
      { value: 'S', text: 'Solved' },
      { value: 'P', text: 'Partially solved' },
      { value: 'B', text: 'Probably solved' },
      { value: 'U', text: 'Unsolved' },
    ],
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

const mapIgvOptionsStateToProps = (state) => {
  const { workspaceNamespace, workspaceName } = getCurrentProject(state)
  return {
    url: `/api/anvil_workspace/${workspaceNamespace}/${workspaceName}/get_igv_options`,
  }
}

const EDIT_IGV_FIELDS = [
  {
    name: 'filePath',
    label: 'IGV File Path',
    component: connect(mapIgvOptionsStateToProps)(LoadOptionsSelect),
    optionsResponseKey: 'igv_options',
    formatOption: value => value,
    errorHeader: 'Unable to Load IGV Files',
    validationErrorHeader: 'No IGV Files Found',
    validationErrorMessage: 'No BAMs or CRAMs were found in the workspace associated with this project',
    validate: validators.required,
  },
]

const EditIndividualButton = ({ project, displayName, fieldName, ...props }) => (
  <BaseFieldView
    field={`${fieldName || 'core'}Edit`}
    idField="individualGuid"
    isEditable={!!project.workspaceName && !project.isAnalystProject && project.canEdit}
    editLabel={`Edit${fieldName || ' Individual'}`}
    modalTitle={`Edit ${displayName}${fieldName || ''}`}
    showErrorPanel
    {...props}
  />
)

EditIndividualButton.propTypes = {
  project: PropTypes.object.isRequired,
  displayName: PropTypes.string,
  fieldName: PropTypes.string,
}

class IndividualRow extends React.PureComponent {

  static propTypes = {
    project: PropTypes.object.isRequired,
    individual: PropTypes.object.isRequired,
    mmeSubmission: PropTypes.object,
    samplesByGuid: PropTypes.object.isRequired,
    alignmentSample: PropTypes.object,
    dispatchUpdateIndividual: PropTypes.func,
    dispatchUpdateIndividualIGV: PropTypes.func,
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
    const {
      project, individual, mmeSubmission, samplesByGuid, tableName, updateIndividualPedigree, alignmentSample,
      dispatchUpdateIndividualIGV,
    } = this.props
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
        <EditIndividualButton
          initialValues={individual}
          project={project}
          displayName={displayName}
          isDeletable
          deleteConfirm={`Are you sure you want to delete ${displayName}? This action can not be undone`}
          formFields={EDIT_INDIVIDUAL_FIELDS}
          onSubmit={updateIndividualPedigree}
        />
        <EditIndividualButton
          fieldName=" IGV"
          initialValues={alignmentSample || individual}
          project={project}
          displayName={displayName}
          formFields={EDIT_IGV_FIELDS}
          onSubmit={dispatchUpdateIndividualIGV}
        />
      </IndividualContainer>
    )

    const editCaseReview = tableName === CASE_REVIEW_TABLE_NAME
    const rightContent = editCaseReview ?
      <CaseReviewStatus individual={individual} /> : (
        <DataDetails
          loadedSamples={loadedSamples}
          individual={individual}
          mmeSubmission={mmeSubmission}
        />
      )

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
  alignmentSample: (
    getIGVSamplesByFamilySampleIndividual(state)[ownProps.individual.familyGuid]?.alignment || {}
  )[ownProps.individual.individualGuid],
})

const mapDispatchToProps = {
  dispatchUpdateIndividual: updateIndividual,
  dispatchUpdateIndividualIGV: values => updateIndividualIGV(values),
  updateIndividualPedigree: values => updateIndividuals({ individuals: [values], delete: values.delete }),
}

export default connect(mapStateToProps, mapDispatchToProps)(IndividualRow)
