import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Label, Popup } from 'semantic-ui-react'
import orderBy from 'lodash/orderBy'

import PedigreeIcon from 'shared/components/icons/PedigreeIcon'
import BaseFieldView from 'shared/components/panel/view-fields/BaseFieldView'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
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

const INHERITANCE_MODE_MAP = {
  S: 'Sporadic',
  D: 'Autosomal dominant inheritance',
  L: 'Sex-limited autosomal dominant',
  A: 'Male-limited autosomal dominant',
  C: 'Autosomal dominant contiguous gene syndrome',
  R: 'Autosomal recessive inheritance',
  G: 'Gonosomal inheritance',
  X: 'X-linked inheritance',
  Z: 'X-linked recessive inheritance',
  Y: 'Y-linked inheritance',
  W: 'X-linked dominant inheritance',
  F: 'Multifactorial inheritance',
  M: 'Mitochondrial inheritance',
}

const AR_FIELDS = {
  arFertilityMeds: 'Fertility medications',
  arIui: 'Intrauterine insemination',
  arIvf: 'In vitro fertilization',
  arIcsi: 'Intra-cytoplasmic sperm injection',
  arSurrogacy: 'Gestational surrogacy',
  arDonoregg: 'Donor egg',
  arDonorsperm: 'Donor sperm',
}

const BLOCK_DISPLAY_STYLE = { display: 'block' }

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

const formatGenes = genes => genes.map(gene =>
  <div key={gene.gene}>{gene.gene} {gene.comments ? ` (${gene.comments.trim()})` : ''}</div>,
)

const AgeDetails = ({ birthYear, deathYear }) => {
  if (!!deathYear || deathYear === 0) {
    return (
      <div>
        Deceased {deathYear > 0 ? `at age ${new Date().getFullYear() - deathYear}` : '(date unknown)'}
        {birthYear > 0 && <div>Born in {birthYear}</div>}
      </div>
    )
  }
  return birthYear > 0 ? new Date().getFullYear() - birthYear : 'Unknown'
}

AgeDetails.propTypes = {
  birthYear: PropTypes.string,
  deathYear: PropTypes.string,
}

const nullableBoolDisplay = (value) => {
  if (value === true) {
    return <Label horizontal basic size="small" content="Yes" color="green" />
  } else if (value === false) {
    return <Label horizontal basic size="small" content="No" color="red" />
  }
  return 'Unknown'
}

const ShowPhenotipsModalButton = () => 'PHENOTIPS'

const INDIVIDUAL_FIELDS = [
  {
    field: 'age',
    fieldName: 'Age',
    isEditable: true,
    editButton: (modalId, initialValues) =>
      <ShowPhenotipsModalButton individual={initialValues} isViewOnly={false} modalId={modalId} />,
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
    field: 'consanguinity',
    fieldName: 'Consanguinity',
    isEditable: true,
    showEmptyValues: true,
    compact: true,
    style: BLOCK_DISPLAY_STYLE,
    editButton: (modalId, initialValues) =>
      <ShowPhenotipsModalButton individual={initialValues} isViewOnly={false} modalId={modalId} />,
    fieldDisplay: nullableBoolDisplay,
    individualFields: ({ affected }) => ({
      isVisible: affected === AFFECTED,
    }),
  },
  {
    field: 'affectedRelatives',
    fieldName: 'Other Affected Relatives',
    isEditable: true,
    showEmptyValues: true,
    compact: true,
    style: BLOCK_DISPLAY_STYLE,
    editButton: (modalId, initialValues) =>
      <ShowPhenotipsModalButton individual={initialValues} isViewOnly={false} modalId={modalId} />,
    fieldDisplay: nullableBoolDisplay,
    individualFields: ({ affected }) => ({
      isVisible: affected === AFFECTED,
    }),
  },
  {
    field: 'expectedInheritance',
    fieldName: 'Expected Mode of Inheritance',
    isEditable: true,
    editButton: (modalId, initialValues) =>
      <ShowPhenotipsModalButton individual={initialValues} isViewOnly={false} modalId={modalId} />,
    fieldDisplay: modes => modes.map(inheritance => INHERITANCE_MODE_MAP[inheritance]).join(', '),
    individualFields: ({ affected }) => ({
      isVisible: affected === AFFECTED,
    }),
  },
  {
    field: 'ar',
    fieldName: 'Assisted Reproduction',
    isEditable: true,
    editButton: (modalId, initialValues) =>
      <ShowPhenotipsModalButton individual={initialValues} isViewOnly={false} modalId={modalId} />,
    fieldDisplay: individual => Object.keys(AR_FIELDS).filter(
      field => individual[field] || individual[field] === false).map(field =>
        <div>{AR_FIELDS[field]}: <b>{individual[field] ? 'Yes' : 'No'}</b></div>,
    ),
    individualFields: individual => ({
      isVisible: individual.affected === AFFECTED,
      fieldValue: individual,
    }),
  },
  {
    field: 'maternalEthnicity',
    fieldName: 'Maternal Ancestry',
    isEditable: true,
    editButton: (modalId, initialValues) =>
      <ShowPhenotipsModalButton individual={initialValues} isViewOnly={false} modalId={modalId} />,
    fieldDisplay: ancestries => ancestries.join(' / '),
  },
  {
    field: 'paternalEthnicity',
    fieldName: 'Paternal Ancestry',
    isEditable: true,
    editButton: (modalId, initialValues) =>
      <ShowPhenotipsModalButton individual={initialValues} isViewOnly={false} modalId={modalId} />,
    fieldDisplay: ancestries => ancestries.join(' / '),
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
    field: 'disorders',
    fieldName: 'Pre-discovery OMIM disorders',
    isEditable: true,
    editButton: (modalId, initialValues) =>
      <ShowPhenotipsModalButton individual={initialValues} isViewOnly={false} modalId={modalId} />,
    fieldDisplay: disorders =>
      disorders.map(mim => <div><a target="_blank" href={`https://www.omim.org/entry/${mim}`}>{mim}</a></div>),
    individualFields: ({ affected }) => ({
      isVisible: affected === AFFECTED,
    }),
  },
  {
    field: 'rejectedGenes',
    fieldName: 'Previously Tested Genes',
    isEditable: true,
    editButton: (modalId, initialValues) =>
      <ShowPhenotipsModalButton individual={initialValues} isViewOnly={false} modalId={modalId} />,
    fieldDisplay: formatGenes,
    individualFields: ({ affected }) => ({
      isVisible: affected === AFFECTED,
    }),
  },
  {
    field: 'candidateGenes',
    fieldName: 'Candidate Genes',
    isEditable: true,
    editButton: (modalId, initialValues) =>
      <ShowPhenotipsModalButton individual={initialValues} isViewOnly={false} modalId={modalId} />,
    fieldDisplay: formatGenes,
    individualFields: ({ affected }) => ({
      isVisible: affected === AFFECTED,
    }),
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
