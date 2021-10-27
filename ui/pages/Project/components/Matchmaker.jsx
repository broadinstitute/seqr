import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Header, Icon, Popup, Label, Grid } from 'semantic-ui-react'
import styled from 'styled-components'

import {
  getIndividualsByGuid, getSortedIndividualsByFamily, getUser, getMmeSubmissionsByGuid, getFamiliesByGuid,
} from 'redux/selectors'
import DeleteButton from 'shared/components/buttons/DeleteButton'
import UpdateButton from 'shared/components/buttons/UpdateButton'
import { BooleanCheckbox, BaseSemanticInput } from 'shared/components/form/Inputs'
import { SubmissionGeneVariants, Phenotypes } from 'shared/components/panel/MatchmakerPanel'
import BaseFieldView from 'shared/components/panel/view-fields/BaseFieldView'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import { Alleles } from 'shared/components/panel/variants/VariantIndividuals'
import Family from 'shared/components/panel/family/Family'
import DataTable, { SelectableTableFormInput } from 'shared/components/table/DataTable'
import DataLoader from 'shared/components/DataLoader'
import { VerticalSpacer } from 'shared/components/Spacers'
import { ButtonLink, ColoredLabel } from 'shared/components/StyledComponents'
import {
  AFFECTED, MATCHMAKER_CONTACT_NAME_FIELD, MATCHMAKER_CONTACT_URL_FIELD, FAMILY_FIELD_MME_NOTES,
} from 'shared/utils/constants'
import { camelcaseToTitlecase } from 'shared/utils/stringUtils'

import {
  loadMmeMatches, updateMmeSubmission, updateMmeSubmissionStatus, sendMmeContactEmail, updateMmeContactNotes,
} from '../reducers'
import {
  getMatchmakerMatchesLoading,
  getIndividualTaggedVariants,
  getDefaultMmeSubmission,
  getMmeResultsBySubmission,
  getMmeDefaultContactEmail,
  getMatchmakerContactNotes,
  getVariantUniqueId,
} from '../selectors'
import SelectSavedVariantsTable from './SelectSavedVariantsTable'

const BreakWordLink = styled.a.attrs({ target: '_blank' })`
  word-break: break-all;
`

const MatchContainer = styled.div`
  word-break: break-all;
`

const PATIENT_CORE_FIELDS = ['id', 'label', 'contact', 'features', 'genomicFeatures']

const MATCH_STATUS_EDIT_FIELDS = [
  { name: 'weContacted', label: 'We Contacted Host', component: BooleanCheckbox, inline: true },
  { name: 'hostContacted', label: 'Host Contacted Us', component: BooleanCheckbox, inline: true },
  { name: 'flagForAnalysis', label: 'Flag for Analysis', component: BooleanCheckbox, inline: true },
  { name: 'deemedIrrelevant', label: 'Deemed Irrelevant', component: BooleanCheckbox, inline: true },
  { name: 'comments', label: 'Comments', component: BaseSemanticInput, inputType: 'TextArea', rows: 5 },
]

const variantSummary =
  variant => `${variant.chrom}:${variant.pos}${variant.alt ? ` ${variant.ref} > ${variant.alt}` : `-${variant.end}`}`

const GENOTYPE_FIELDS = [
  { name: 'geneSymbol', content: 'Gene', width: 2 },
  { name: 'xpos', content: 'Variant', width: 3, format: val => variantSummary(val) },
  { name: 'numAlt', content: 'Genotype', width: 2, format: val => <Alleles variant={val} genotype={val} /> },
  {
    name: 'tags',
    content: 'Tags',
    width: 8,
    format: val => val.tags.map(
      tag => <ColoredLabel key={tag.tagGuid} size="small" color={tag.color} horizontal content={tag.name} />,
    ),
  },
]

const mapGenotypesStateToProps = (state, ownProps) => {
  const individualGuid = ownProps.meta.form.split('_-_')[0]
  const { familyGuid } = state.individualsByGuid[individualGuid]
  return {
    data: getIndividualTaggedVariants(state, { individualGuid }),
    familyGuid,
  }
}

const EditGenotypesTable = connect(mapGenotypesStateToProps)(SelectSavedVariantsTable)

const PHENOTYPE_FIELDS = [
  { name: 'id', content: 'HPO ID', width: 4 },
  { name: 'label', content: 'Description', width: 11 },
]

const EMPTY_LIST = []

const updateIndividualFeatures = (onChange, individual) => newValue => onChange(
  individual.features.filter(feature => newValue[feature.id]).map(feature => ({ observed: 'yes', ...feature })),
)

const BaseEditPhenotypesTable = React.memo(({ individual, value, onChange }) => (
  <SelectableTableFormInput
    idField="id"
    defaultSortColumn="label"
    columns={PHENOTYPE_FIELDS}
    data={individual.features || EMPTY_LIST}
    value={value}
    onChange={updateIndividualFeatures(onChange, individual)}
  />
))

BaseEditPhenotypesTable.propTypes = {
  individual: PropTypes.object,
  value: PropTypes.object,
  onChange: PropTypes.func,
}

const mapPhenotypeStateToProps = (state, ownProps) => ({
  individual: getIndividualsByGuid(state)[ownProps.meta.form.split('_-_')[0]],
})

const EditPhenotypesTable = connect(mapPhenotypeStateToProps)(BaseEditPhenotypesTable)

const CONTACT_URL_REGEX = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}(,\s*[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{1,4})*$/i
const SUBMISSION_EDIT_FIELDS = [
  { ...MATCHMAKER_CONTACT_NAME_FIELD, name: 'contactName' },
  { ...MATCHMAKER_CONTACT_URL_FIELD, name: 'contactHref' },
  {
    name: 'geneVariants',
    component: EditGenotypesTable,
    idField: 'variantId',
    columns: GENOTYPE_FIELDS,
    includeSelectedRowData: true,
    normalize: (val, prevVal) => (typeof val === 'boolean' ? prevVal : Object.values(val || {}).filter(v => v)),
    format: value => (value || []).reduce(
      (acc, variant) => ({ ...acc, [variant.variantId || getVariantUniqueId(variant)]: variant }), {},
    ),
  },
  {
    name: 'phenotypes',
    component: EditPhenotypesTable,
    format: value => value.reduce((acc, feature) => ({ ...acc, [feature.id]: true }), {}),
    validate: (val, allValues) => ((val && val.length) || (allValues.geneVariants && allValues.geneVariants.length) ?
      undefined : 'Genotypes and/or phenotypes are required'),
  },
]

const CONTACT_FIELDS = [
  {
    name: 'to',
    label: 'Send To:',
    validate: val => (CONTACT_URL_REGEX.test(val) ? undefined : 'Invalid Contact Email'),
  },
  { name: 'subject', label: 'Subject:' },
  { name: 'body', component: BaseSemanticInput, inputType: 'TextArea', rows: 12 },
]

const BaseContactHostButton = React.memo(({ defaultContactEmail, onSubmit }) => (
  <UpdateButton
    onSubmit={onSubmit}
    initialValues={defaultContactEmail}
    formFields={CONTACT_FIELDS}
    modalTitle={`Send Contact Email for Patient ${defaultContactEmail.patientId}`}
    modalId={`contactEmail-${defaultContactEmail.patientId}`}
    buttonText="Contact Host"
    editIconName="mail"
    showErrorPanel
    submitButtonText="Send"
    buttonFloated="right"
  />
))

BaseContactHostButton.propTypes = {
  defaultContactEmail: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapContactButtonStateToProps = (state, ownProps) => ({
  defaultContactEmail: getMmeDefaultContactEmail(state, ownProps),
})

const mapContactDispatchToProps = {
  onSubmit: sendMmeContactEmail,
}

const ContactHostButton = connect(mapContactButtonStateToProps, mapContactDispatchToProps)(BaseContactHostButton)

const contactedLabel = (val) => {
  if (val.hostContacted) {
    return 'Host Contacted Us'
  }
  return val.weContacted ? 'We Contacted Host' : 'Not Contacted'
}

const displayMatchStatus = val => (
  <div>
    <Label horizontal content={contactedLabel(val)} color={val.hostContacted || val.weContacted ? 'green' : 'orange'} />
    {val.flagForAnalysis && <Label horizontal content="Flag for Analysis" color="purple" />}
    {val.deemedIrrelevant && <Label horizontal content="Deemed Irrelevant" color="red" />}
    <p>{val.comments}</p>
    <ContactHostButton matchmakerResultGuid={val.matchmakerResultGuid} />
  </div>
)

const BaseMatchStatus = React.memo(({ initialValues, onSubmit }) => (
  <BaseFieldView
    initialValues={initialValues}
    field="matchStatus"
    idField="matchmakerResultGuid"
    compact
    isEditable
    showErrorPanel
    modalTitle="Edit MME Submission Status"
    formFields={MATCH_STATUS_EDIT_FIELDS}
    onSubmit={onSubmit}
    fieldDisplay={displayMatchStatus}
  />
))

BaseMatchStatus.propTypes = {
  initialValues: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapStatusDispatchToProps = {
  onSubmit: updateMmeSubmissionStatus,
}

const MatchStatus = connect(null, mapStatusDispatchToProps)(BaseMatchStatus)

const BaseContactNotes = React.memo(({ contact, user, contactNote, onSubmit, ...props }) => (
  <TextFieldView
    isVisible={user.isAnalyst}
    fieldName="Contact Notes"
    field="comments"
    idField="contactInstitution"
    initialValues={contactNote || contact}
    isEditable
    modalTitle={`Edit Shared Notes for "${contact.institution}"`}
    onSubmit={onSubmit}
    {...props}
  />
))

BaseContactNotes.propTypes = {
  contact: PropTypes.object,
  contactNote: PropTypes.object,
  user: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapContactNotesStateToProps = (state, ownProps) => ({
  user: getUser(state),
  contactNote: getMatchmakerContactNotes(state)[(ownProps.contact.institution || '').toLowerCase()],
})

const mapContactNotesDispatchToProps = {
  onSubmit: updateMmeContactNotes,
}

const ContactNotes = connect(mapContactNotesStateToProps, mapContactNotesDispatchToProps)(BaseContactNotes)

const formatYesNo = bool => (bool ? 'Yes' : 'No')

const DISPLAY_FIELDS = [
  {
    name: 'id',
    width: 2,
    content: 'Match',
    verticalAlign: 'top',
    format: (val, isDownload) => {
      const patientFields = Object.keys(val.patient).filter(k => val.patient[k] && !PATIENT_CORE_FIELDS.includes(k))
      let displayName = val.id
      if (val.patient.label) {
        displayName = val.patient.label
        patientFields.unshift('id')
      }
      if (isDownload) {
        return displayName
      }
      if (val.originatingSubmission) {
        const href = `/project/${val.originatingSubmission.projectGuid}/family_page/${val.originatingSubmission.familyGuid}/matchmaker_exchange`
        displayName = <Link to={href} target="_blank">{displayName}</Link>
      }
      return patientFields.length ? (
        <Popup
          header="Patient Details"
          trigger={
            <MatchContainer>
              {displayName}
              &nbsp;
              <Icon link name="info circle" />
            </MatchContainer>
          }
          content={patientFields.map(k => (
            <div key={k}>
              <b>{`${camelcaseToTitlecase(k)}: `}</b>
              {k === 'disorders' ? val.patient[k].map(({ id }) => id).join(', ') : val.patient[k]}
            </div>
          ))}
        />
      ) : <MatchContainer>{displayName}</MatchContainer>
    },
  },
  {
    name: 'createdDate',
    width: 2,
    content: 'First Seen',
    verticalAlign: 'top',
    format: val => new Date(val.createdDate).toLocaleDateString(),
  },
  {
    name: 'contact',
    width: 3,
    content: 'Contact',
    verticalAlign: 'top',
    format: ({ patient }, isDownload) => patient.contact && (isDownload ?
      patient.contact.institution || patient.contact.name : (
        <div>
          <div><b>{patient.contact.institution}</b></div>
          <div>{patient.contact.name}</div>
          {patient.contact.email && (
            <div>
              <BreakWordLink href={patient.contact.email}>{patient.contact.email.replace('mailto:', '')}</BreakWordLink>
            </div>
          )}
          <BreakWordLink href={patient.contact.href}>{patient.contact.href.replace('mailto:', '')}</BreakWordLink>
          <VerticalSpacer height={10} />
          <ContactNotes contact={patient.contact} modalId={patient.id} />
        </div>
      )),
  },
  {
    name: 'geneVariants',
    width: 2,
    content: 'Genes',
    verticalAlign: 'top',
    downloadColumn: 'We Contacted Host',
    format: (val, isDownload) => (
      isDownload ? formatYesNo(val.weContacted) :
      <SubmissionGeneVariants geneVariants={val.geneVariants} modalId={val.id} />
    ),
  },
  {
    name: 'phenotypes',
    width: 3,
    content: 'Phenotypes',
    verticalAlign: 'top',
    downloadColumn: 'Host Contacted Us',
    format: (val, isDownload) => (
      isDownload ? formatYesNo(val.hostContacted) : <Phenotypes phenotypes={val.phenotypes} />
    ),
  },
  {
    name: 'comments',
    width: 4,
    content: 'Follow Up Status',
    verticalAlign: 'top',
    downloadColumn: 'Notes',
    format: (initialValues, isDownload) => (
      isDownload ? initialValues.comments : <MatchStatus initialValues={initialValues} />
    ),
  },
]

const BaseMatchmakerIndividual = React.memo((
  { loading, load, searchMme, individual, onSubmit, defaultMmeSubmission, mmeResults, mmeSubmission },
) => (
  <div>
    <VerticalSpacer height={10} />
    <Header size="medium" content={individual.displayName} dividing />
    {mmeSubmission && !mmeSubmission.deletedDate ? (
      <Grid padded>
        <Grid.Row>
          <Grid.Column width={2}><b>Submitted Genotypes:</b></Grid.Column>
          <Grid.Column width={14}>
            {mmeSubmission.geneVariants && mmeSubmission.geneVariants.length ? (
              <SubmissionGeneVariants
                geneVariants={mmeSubmission.geneVariants}
                modalId="submission"
                horizontal
              />
            ) : <i>None</i>}
          </Grid.Column>
        </Grid.Row>
        <Grid.Row>
          <Grid.Column width={2}><b>Submitted Phenotypes:</b></Grid.Column>
          <Grid.Column width={14}>
            {mmeSubmission.phenotypes && mmeSubmission.phenotypes.length ?
              <Phenotypes phenotypes={mmeSubmission.phenotypes} horizontal /> : <i>None</i>}
          </Grid.Column>
        </Grid.Row>
      </Grid>
    ) : (
      <div>
        <Header
          size="small"
          content="This individual has no submissions"
          icon={<Icon name="warning sign" color="orange" />}
          subheader={
            <div className="sub header">
              <UpdateButton
                initialValues={defaultMmeSubmission}
                buttonText="Submit to Matchmaker"
                editIconName=" "
                modalSize="large"
                modalTitle={`Create Submission for ${individual.displayName}`}
                modalId={`${individual.individualGuid}_-_createMmeSubmission`}
                confirmDialog="Are you sure you want to submit this individual?"
                formFields={SUBMISSION_EDIT_FIELDS}
                onSubmit={onSubmit}
                showErrorPanel
              />
            </div>
          }
        />
      </div>
    )}
    <DataLoader content load={load} loading={false}>
      {mmeSubmission && !mmeSubmission.deletedDate && (
        <div>
          <ButtonLink
            disabled={loading}
            onClick={searchMme}
            icon="search"
            labelPosition="right"
            content="Search for New Matches"
          />
          | &nbsp; &nbsp;
          <UpdateButton
            disabled={loading}
            buttonText="Update Submission"
            modalSize="large"
            modalTitle={`Update Submission for ${individual.displayName}`}
            modalId={`${individual.individualGuid}_-_updateMmeSubmission`}
            confirmDialog="Are you sure you want to update this submission?"
            initialValues={mmeSubmission}
            formFields={SUBMISSION_EDIT_FIELDS}
            onSubmit={onSubmit}
            showErrorPanel
          />
          | &nbsp; &nbsp;
          <DeleteButton
            disabled={loading}
            onSubmit={onSubmit}
            buttonText="Delete Submission"
            confirmDialog="Are you sure you want to remove this patient from the Matchmaker Exchange"
          />
          <DataTable
            basic="very"
            fixed
            idField="id"
            defaultSortColumn="createdDate"
            defaultSortDescending
            columns={DISPLAY_FIELDS}
            data={mmeResults.active}
            loading={loading}
            emptyContent="No matches found"
            downloadFileName={`MME_matches_${individual.displayName}`}
            downloadAlign="none"
          />
        </div>
      )}
      {mmeResults && mmeResults.removed && mmeResults.removed.length > 0 && (
        <div>
          <VerticalSpacer height={10} />
          <Header dividing disabled size="medium" content="Previous Matches" />
          <DataTable
            basic="very"
            fixed
            idField="id"
            defaultSortColumn="createdDate"
            defaultSortDescending
            columns={DISPLAY_FIELDS}
            data={mmeResults.removed}
            loading={loading}
          />
        </div>
      )}
    </DataLoader>
  </div>
))

BaseMatchmakerIndividual.propTypes = {
  individual: PropTypes.object.isRequired,
  loading: PropTypes.bool,
  load: PropTypes.func,
  searchMme: PropTypes.func,
  onSubmit: PropTypes.func,
  defaultMmeSubmission: PropTypes.object,
  mmeResults: PropTypes.object,
  mmeSubmission: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  loading: getMatchmakerMatchesLoading(state),
  defaultMmeSubmission: getDefaultMmeSubmission(state),
  mmeSubmission: getMmeSubmissionsByGuid(state)[ownProps.individual.mmeSubmissionGuid],
  mmeResults: getMmeResultsBySubmission(state, ownProps)[ownProps.individual.mmeSubmissionGuid],
})

const mapDispatchToProps = (dispatch, ownProps) => ({
  load: () => dispatch(loadMmeMatches(ownProps.individual.mmeSubmissionGuid, false)),
  searchMme: () => dispatch(loadMmeMatches(ownProps.individual.mmeSubmissionGuid, true)),
  onSubmit: values => dispatch(updateMmeSubmission({
    ...values,
    submissionGuid: ownProps.individual.mmeSubmissionGuid,
    individualGuid: ownProps.individual.individualGuid,
  })),
})

const MatchmakerIndividual = connect(mapStateToProps, mapDispatchToProps)(BaseMatchmakerIndividual)

const MME_FAMILY_FIELDS = [{ id: FAMILY_FIELD_MME_NOTES, colWidth: 16 }]

const Matchmaker = React.memo(({ individuals, family }) => (
  <div>
    <Header dividing size="medium" content="Notes" />
    <Family family={family} compact useFullWidth hidePedigree fields={MME_FAMILY_FIELDS} />
    {(individuals || []).filter(individual => individual.affected === AFFECTED).map(
      individual => <MatchmakerIndividual key={individual.individualGuid} individual={individual} />,
    )}
  </div>
))

Matchmaker.propTypes = {
  family: PropTypes.object,
  individuals: PropTypes.arrayOf(PropTypes.object),
}

const mapIndividualsStateToProps = (state, ownProps) => ({
  family: getFamiliesByGuid(state)[ownProps.match.params.familyGuid],
  individuals: getSortedIndividualsByFamily(state)[ownProps.match.params.familyGuid],
})

export default connect(mapIndividualsStateToProps)(Matchmaker)
