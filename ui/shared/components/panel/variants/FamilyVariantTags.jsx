import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'
import { Icon, Popup, Table, Label } from 'semantic-ui-react'
import styled from 'styled-components'

import { updateVariantNote, updateVariantTags } from 'redux/rootReducer'
import {
  getFamiliesByGuid,
  getVariantTagNotesByFamilyVariants,
  getSelectableTagTypesByProject,
  getFunctionalTagTypesTypesByProject,
  getVariantId,
  getMmeSubmissionsByGuid,
  getGenesById,
  getUser,
} from 'redux/selectors'
import { DISCOVERY_CATEGORY_NAME, MME_TAG_NAME, GREGOR_FINDING_TAG_NAME } from 'shared/utils/constants'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'
import VariantClassify from './VariantClassify'
import PopupWithModal from '../../PopupWithModal'
import { HorizontalSpacer } from '../../Spacers'
import { NoBorderTable, InlineHeader } from '../../StyledComponents'
import FamilyLink from '../../buttons/FamilyLink'
import { StyledForm } from '../../form/FormHelpers'
import { InlineToggle, BooleanCheckbox } from '../../form/Inputs'
import NoteListFieldView from '../view-fields/NoteListFieldView'
import TagFieldView from '../view-fields/TagFieldView'

const TagTitle = styled.span`
  font-weight: bolder;
  color: #999;
`

const NO_DISPLAY = { display: 'none' }

const SHORTCUT_TAGS = ['Review', 'Excluded']

const VARIANT_NOTE_FIELDS = [{
  name: 'saveAsGeneNote',
  label: 'Add to public gene notes',
  component: BooleanCheckbox,
}]

const ANALYST_VARIANT_NOTE_FIELDS = [{
  name: 'report',
  label: 'Include in report notes',
  component: BooleanCheckbox,
}, ...VARIANT_NOTE_FIELDS,
]

const DEPRECATED_MME_TAG = 'seqr MME (old)'
const AIP_TAG_TYPE = 'AIP'
const NO_EDIT_TAG_TYPES = [AIP_TAG_TYPE, GREGOR_FINDING_TAG_NAME]
const TAG_TYPE_TILES = {
  [AIP_TAG_TYPE]: 'Categories',
  [GREGOR_FINDING_TAG_NAME]: 'Finding Detail',
}

const aipCategoryContent = (key, { name, date }) => ([
  <Table.HeaderCell key="name" content={`${key} - ${name} `} />,
  <Table.Cell key="date" disabled content={`(${new Date(date).toLocaleDateString()})`} />,
])

const structuredMetadataRow = ([key, value]) => (
  <Table.Row key={key}>
    {typeof value === 'string' ? [
      <Table.HeaderCell key="key" textAlign="right" content={snakecaseToTitlecase(key)} />,
      <Table.Cell key="value" content={value} />,
    ] : aipCategoryContent(key, value)}
  </Table.Row>
)

export const taggedByPopup = (tag, title) => (trigger, hideMetadata) => (
  <Popup
    position="top right"
    size="tiny"
    trigger={trigger}
    header={title || (tag.structuredMetadata ? TAG_TYPE_TILES[tag.name] : 'Tagged by')}
    hoverable
    flowing
    content={
      <div>
        {tag.structuredMetadata ? (
          <NoBorderTable basic="very" compact="very">
            <Table.Body>
              {Object.entries(tag.structuredMetadata).filter(e => e[0] !== 'removed').map(structuredMetadataRow)}
              {tag.structuredMetadata.removed && [
                <Table.Row key="removedHeader"><Table.HeaderCell colSpan={2} content="Removed Categories" /></Table.Row>,
                ...Object.entries(tag.structuredMetadata.removed).map(structuredMetadataRow),
              ]}
            </Table.Body>
          </NoBorderTable>
        ) : `${tag.createdBy || 'unknown user'}${tag.lastModifiedDate ? ` on ${new Date(tag.lastModifiedDate).toLocaleDateString()}` : ''}`}
        {tag.metadata && !hideMetadata && (
          <div>
            {tag.metadataTitle ? (
              <span>
                <b>{`${tag.metadataTitle}: `}</b>
                {tag.metadata}
              </span>
            ) : <i>{tag.metadata}</i>}
          </div>
        )}
        {tag.searchHash && <div><NavLink to={`/variant_search/results/${tag.searchHash}`}>Re-run search</NavLink></div>}
      </div>
    }
  />
)

const notePopup = note => note && taggedByPopup(note, 'Note By')

const ShortcutTagToggle = React.memo(({ tag, ...props }) => {
  const toggle = <InlineToggle color={tag && tag.color} divided {...props} value={tag} />
  return tag ? taggedByPopup(tag)(toggle) : toggle
})

ShortcutTagToggle.propTypes = {
  tag: PropTypes.object,
}

const ShortcutTags = React.memo(({ variantTagNotes, dispatchUpdateFamilyVariantTags }) => {
  const { tags = [], ...variantMeta } = variantTagNotes || {}
  const onSubmit = tagName => value => dispatchUpdateFamilyVariantTags({
    ...variantMeta,
    tags: value ? [...tags, { name: tagName }] : tags.filter(tag => tag.name !== tagName),
  })

  return (
    <StyledForm inline hasSubmitButton={false}>
      {SHORTCUT_TAGS.map(tagName => (
        <ShortcutTagToggle
          key={tagName}
          label={tagName}
          tag={tags.find(tag => tag.name === tagName)}
          onChange={onSubmit(tagName)}
        />
      ))}
    </StyledForm>
  )
})

ShortcutTags.propTypes = {
  variantTagNotes: PropTypes.object,
  dispatchUpdateFamilyVariantTags: PropTypes.func.isRequired,
}

const validateTags = tags => (tags?.filter(({ category }) => category === DISCOVERY_CATEGORY_NAME).length > 1 ?
  'Only 1 Discovery Tag can be added' : undefined
)

const VariantTagField = React.memo(({ variantTagNotes, variantId, fieldName, family, ...props }) => (
  <TagFieldView
    idField="variantGuids"
    defaultId={variantId}
    modalId={family.familyGuid}
    modalTitle={`Edit Variant ${fieldName} for Family ${family.displayName} for ${
      variantId.split(',').map((vId) => {
        const [chrom, pos, ref, alt] = vId.split('-')
        return `chr${chrom}:${pos} ${ref} > ${alt}`
      }).join(', ')}`}
    modalSize="large"
    editLabel={`Edit ${fieldName}`}
    initialValues={variantTagNotes}
    compact
    isEditable
    popup={taggedByPopup}
    validate={validateTags}
    {...props}
  />
))

VariantTagField.propTypes = {
  variantTagNotes: PropTypes.object,
  fieldName: PropTypes.string.isRequired,
  variantId: PropTypes.string.isRequired,
  family: PropTypes.object.isRequired,
}

const VariantLink = React.memo(({ variant, variantTagNotes, family }) => (
  <NavLink
    to={variantTagNotes ?
      `/project/${family.projectGuid}/saved_variants/variant/${variantTagNotes.variantGuids}` :
      `/variant_search/variant/${variant.variantId}/family/${family.familyGuid}`}
    activeStyle={NO_DISPLAY}
  >
    <Popup
      trigger={<Icon name="linkify" link />}
      content={`Go to the page for this individual variant ${(Array.isArray(variant) ?
        variant : [variant]).map(v => (v ? `chr${v.chrom}:${v.pos} ${v.ref} > ${v.alt}` : 'variant')).join(', ')} from family ${family.familyId}. Note: There is no additional information on this page, it is intended for sharing specific variants.`}
      position="right center"
      wide
    />
  </NavLink>
))

VariantLink.propTypes = {
  variant: PropTypes.oneOfType([PropTypes.object, PropTypes.array]).isRequired,
  variantTagNotes: PropTypes.object,
  family: PropTypes.object.isRequired,
}

const FamilyLabel = React.memo(props => (
  <InlineHeader size="small">
    Family
    <HorizontalSpacer width={5} />
    <FamilyLink PopupClass={PopupWithModal} {...props} />
  </InlineHeader>
))

FamilyLabel.propTypes = {
  family: PropTypes.object.isRequired,
}

export const LoadedFamilyLabel = connect((state, ownProps) => ({
  family: getFamiliesByGuid(state)[ownProps.familyGuid],
}))(FamilyLabel)

const MatchmakerLabel = ({ variant, family, mmeSubmissionsByGuid, genesById }) => {
  const variantSubmissions = (Array.isArray(variant) ? variant.reduce(
    (acc, { mmeSubmissions = [] }) => ([...acc, ...mmeSubmissions]), [],
  ) : (variant.mmeSubmissions || [])).map(
    ({ submissionGuid, geneId }) => ({ gene: genesById[geneId], submission: mmeSubmissionsByGuid[submissionGuid] }),
  ).filter(({ submission }) => family.individualGuids.includes(submission.individualGuid))
  return variantSubmissions.length ? (
    <Popup
      content={[...new Set(variantSubmissions.map(
        ({ gene, submission }) => `${gene.geneSymbol} submitted ${new Date(submission.lastModifiedDate).toLocaleDateString()}`,
      ))].join('; ')}
      trigger={<Label
        as={NavLink}
        to={`/project/${family.projectGuid}/family_page/${family.familyGuid}/matchmaker_exchange`}
        target="_blank"
        content={MME_TAG_NAME}
        color="violet"
        size="small"
      />}
    />
  ) : null
}

MatchmakerLabel.propTypes = {
  variant: PropTypes.oneOfType([PropTypes.object, PropTypes.array]).isRequired,
  family: PropTypes.object.isRequired,
  mmeSubmissionsByGuid: PropTypes.object,
  genesById: PropTypes.object,
}

const FamilyVariantTags = React.memo(({
  variant, variantTagNotes, family, projectTagTypes, projectFunctionalTagTypes, dispatchUpdateVariantNote,
  dispatchUpdateFamilyVariantTags, dispatchUpdateFamilyVariantFunctionalTags, isCompoundHet, variantId,
  linkToSavedVariants, mmeSubmissionsByGuid, genesById, user,
}) => (
  family ? (
    <NoBorderTable basic="very" compact="very" celled>
      <Table.Body>
        <Table.Row verticalAlign="top">
          {!isCompoundHet && (
            <Table.Cell collapsing>
              <FamilyLabel family={family} path={linkToSavedVariants ? `saved_variants/family/${family.familyGuid}` : null} />
            </Table.Cell>
          )}
          <Table.Cell collapsing textAlign="right">
            <TagTitle>Tags:</TagTitle>
          </Table.Cell>
          {!isCompoundHet && (
            <Table.Cell collapsing>
              <ShortcutTags
                variantTagNotes={variantTagNotes}
                dispatchUpdateFamilyVariantTags={dispatchUpdateFamilyVariantTags}
              />
            </Table.Cell>
          )}
          <Table.Cell>
            <VariantTagField
              field="tags"
              fieldName="Tags"
              family={family}
              variantTagNotes={variantTagNotes}
              variantId={variantId}
              tagOptions={projectTagTypes}
              displayMetadata
              disabledTagType={DEPRECATED_MME_TAG}
              noEditTagTypes={NO_EDIT_TAG_TYPES}
              onSubmit={dispatchUpdateFamilyVariantTags}
            />
            <HorizontalSpacer width={5} />
            {((variantTagNotes || {}).tags || []).some(tag => tag.category === DISCOVERY_CATEGORY_NAME) && (
              <span>
                <TagTitle>Fxnl Data:</TagTitle>
                <VariantTagField
                  field="functionalData"
                  fieldName="Fxnl Data"
                  family={family}
                  variantTagNotes={variantTagNotes}
                  variantId={variantId}
                  tagOptions={projectFunctionalTagTypes}
                  onSubmit={dispatchUpdateFamilyVariantFunctionalTags}
                />
              </span>
            )}
          </Table.Cell>
          <Table.Cell collapsing textAlign="right">
            {variant.variantGuid && !Array.isArray(variant) &&
              <VariantClassify variant={variant} familyGuid={family.familyGuid} />}
          </Table.Cell>
          <Table.Cell collapsing textAlign="right">
            {(!Array.isArray(variant) || variantTagNotes) &&
              <VariantLink variant={variant} variantTagNotes={variantTagNotes} family={family} />}
          </Table.Cell>
        </Table.Row>
        <Table.Row verticalAlign="top">
          {!isCompoundHet && (
            <Table.Cell collapsing>
              <MatchmakerLabel
                family={family}
                variant={variant}
                mmeSubmissionsByGuid={mmeSubmissionsByGuid}
                genesById={genesById}
              />
            </Table.Cell>
          )}
          <Table.Cell collapsing textAlign="right">
            <TagTitle>Notes:</TagTitle>
          </Table.Cell>
          <Table.Cell colSpan={isCompoundHet ? 3 : 4}>
            <NoteListFieldView
              initialValues={variantTagNotes}
              modalId={family.familyGuid}
              modalTitle={`Variant Note for Family ${family.displayName}`}
              additionalEditFields={user.isAnalyst ? ANALYST_VARIANT_NOTE_FIELDS : VARIANT_NOTE_FIELDS}
              defaultId={variantId}
              idField="variantGuids"
              isEditable
              showInLine
              compact
              getTextPopup={notePopup}
              onSubmit={dispatchUpdateVariantNote}
            />
          </Table.Cell>
        </Table.Row>
      </Table.Body>
    </NoBorderTable>
  ) : null
))

FamilyVariantTags.propTypes = {
  variant: PropTypes.oneOfType([PropTypes.object, PropTypes.array]).isRequired,
  variantTagNotes: PropTypes.object,
  variantId: PropTypes.string.isRequired,
  family: PropTypes.object.isRequired,
  projectTagTypes: PropTypes.arrayOf(PropTypes.object).isRequired,
  projectFunctionalTagTypes: PropTypes.arrayOf(PropTypes.object).isRequired,
  isCompoundHet: PropTypes.bool,
  linkToSavedVariants: PropTypes.bool,
  dispatchUpdateVariantNote: PropTypes.func.isRequired,
  dispatchUpdateFamilyVariantTags: PropTypes.func.isRequired,
  dispatchUpdateFamilyVariantFunctionalTags: PropTypes.func.isRequired,
  mmeSubmissionsByGuid: PropTypes.object,
  genesById: PropTypes.object,
  user: PropTypes.object,
}

FamilyVariantTags.defaultProps = {
  isCompoundHet: false,
  linkToSavedVariants: false,
}

const mapStateToProps = (state, ownProps) => {
  const variantId = getVariantId(ownProps.variant)
  const family = getFamiliesByGuid(state)[ownProps.familyGuid]
  const { projectGuid } = family || {}
  return {
    variantId,
    family,
    projectTagTypes: getSelectableTagTypesByProject(state)[projectGuid],
    projectFunctionalTagTypes: getFunctionalTagTypesTypesByProject(state)[projectGuid],
    variantTagNotes: ((getVariantTagNotesByFamilyVariants(state) || {})[ownProps.familyGuid] || {})[variantId],
    mmeSubmissionsByGuid: getMmeSubmissionsByGuid(state),
    genesById: getGenesById(state),
    user: getUser(state),
  }
}

const mapDispatchToProps = (dispatch, ownProps) => ({
  dispatchUpdateVariantNote: updates => dispatch(
    updateVariantNote({ ...updates, variant: ownProps.variant, familyGuid: ownProps.familyGuid }),
  ),
  dispatchUpdateFamilyVariantTags: updates => dispatch(
    updateVariantTags({ ...updates, variant: ownProps.variant, familyGuid: ownProps.familyGuid }),
  ),
  dispatchUpdateFamilyVariantFunctionalTags: updates => dispatch(
    updateVariantTags({ ...updates, variant: ownProps.variant, familyGuid: ownProps.familyGuid }, 'functional_data'),
  ),
})

export default connect(mapStateToProps, mapDispatchToProps)(FamilyVariantTags)
