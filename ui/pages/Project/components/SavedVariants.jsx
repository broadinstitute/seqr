import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Route, Switch, Link } from 'react-router-dom'
import { Grid } from 'semantic-ui-react'
import styled from 'styled-components'

import { updateVariantTags } from 'redux/rootReducer'
import { getCurrentAnalysisGroupFamilyGuids } from 'redux/selectors'
import {
  VARIANT_SORT_FIELD,
  VARIANT_HIDE_EXCLUDED_FIELD,
  VARIANT_HIDE_REVIEW_FIELD,
  VARIANT_HIDE_KNOWN_GENE_FOR_PHENOTYPE_FIELD,
  VARIANT_PER_PAGE_FIELD,
  EXCLUDED_TAG_NAME,
  REVIEW_TAG_NAME,
  DISCOVERY_CATEGORY_NAME,
  SHOW_ALL,
} from 'shared/utils/constants'
import UpdateButton from 'shared/components/buttons/UpdateButton'
import { LargeMultiselect, Dropdown } from 'shared/components/form/Inputs'
import SavedVariants from 'shared/components/panel/variants/SavedVariants'

import { TAG_FORM_FIELD } from '../constants'
import { loadSavedVariants, updateSavedVariantTable } from '../reducers'
import {
  getCurrentProject, getProjectTagTypeOptions, getTaggedVariantsByFamily, getProjectVariantSavedByOptions,
  getSavedVariantTagTypeCounts, getSavedVariantTagTypeCountsByFamily, getSavedVariantTableState,
} from '../selectors'
import VariantTagTypeBar, { getSavedVariantsLinkPath } from './VariantTagTypeBar'
import SelectSavedVariantsTable, { TAG_COLUMN, VARIANT_POS_COLUMN, GENES_COLUMN } from './SelectSavedVariantsTable'

const LabelLink = styled(Link)`
  color: black;
  
  &:hover {
    color: black;
  }
`

const mapSavedByInputStateToProps = state => ({
  options: getProjectVariantSavedByOptions(state),
})

const FILTER_FIELDS = [
  VARIANT_SORT_FIELD,
  VARIANT_HIDE_KNOWN_GENE_FOR_PHENOTYPE_FIELD,
  VARIANT_HIDE_EXCLUDED_FIELD,
  VARIANT_HIDE_REVIEW_FIELD,
  VARIANT_PER_PAGE_FIELD,
  {
    name: 'savedBy',
    component: connect(mapSavedByInputStateToProps)(Dropdown),
    inline: true,
    selection: false,
    fluid: false,
    label: 'Saved By:',
    placeholder: 'Select a user',
  },
]
const NON_DISCOVERY_FILTER_FIELDS = FILTER_FIELDS.filter(({ name }) => name !== 'hideKnownGeneForPhenotype')

const EXCLUDED_TAGS = [EXCLUDED_TAG_NAME]
const REVIEW_TAGS = [REVIEW_TAG_NAME]
const EXCLUDED_AND_REVIEW_TAGS = [...EXCLUDED_TAGS, ...REVIEW_TAGS]

const mapVariantLinkStateToProps = (state, ownProps) => {
  const familyGuid = ownProps.meta.data.formId
  return {
    data: getTaggedVariantsByFamily(state)[familyGuid],
    familyGuid,
  }
}

const mapTagInputStateToProps = state => ({
  options: getProjectTagTypeOptions(state),
})

const LINK_VARIANT_FIELDS = [
  {
    component: connect(mapTagInputStateToProps)(LargeMultiselect),
    ...TAG_FORM_FIELD,
  },
  {
    name: 'variantGuids',
    idField: 'variantGuid',
    component: connect(mapVariantLinkStateToProps)(SelectSavedVariantsTable),
    columns: [
      GENES_COLUMN,
      VARIANT_POS_COLUMN,
      TAG_COLUMN,
    ],
    includeSelectedRowData: true,
    validate: (value) => {
      const variants = Object.values(value || {}).filter(v => v)
      if (variants.length < 2) {
        return 'Multiple variants required'
      }
      if (variants.length === 2 &&
        Object.keys(variants[0].transcripts).every(geneId => !variants[1].transcripts[geneId])
      ) {
        return 'Compound het pairs must be in the same gene'
      }
      return undefined
    },
  },
]

const BaseLinkSavedVariants = ({ familyGuid, onSubmit }) => (
  <UpdateButton
    modalTitle="Link Saved Variants"
    modalId={`${familyGuid}-linkVariants`}
    formMetaId={familyGuid}
    buttonText="Link Variants"
    editIconName="linkify"
    size="medium"
    formFields={LINK_VARIANT_FIELDS}
    onSubmit={onSubmit}
    showErrorPanel
  />
)

BaseLinkSavedVariants.propTypes = {
  familyGuid: PropTypes.string,
  onSubmit: PropTypes.func,
}

const mapVariantDispatchToProps = (dispatch, { familyGuid }) => ({
  onSubmit: (values) => {
    const variantGuids = Object.keys(values.variantGuids).filter(
      variantGuid => values.variantGuids[variantGuid],
    ).join(',')
    dispatch(updateVariantTags({ ...values, familyGuid, variantGuids }))
  },
})

const LinkSavedVariants = connect(null, mapVariantDispatchToProps)(BaseLinkSavedVariants)

class BaseProjectSavedVariants extends React.PureComponent {

  static propTypes = {
    match: PropTypes.object,
    project: PropTypes.object,
    analysisGroupFamilyGuids: PropTypes.arrayOf(PropTypes.string),
    tagTypeCounts: PropTypes.object,
    updateTableField: PropTypes.func,
    loadProjectSavedVariants: PropTypes.func,
    categoryFilter: PropTypes.string,
  }

  getUpdateTagUrl = (newTag) => {
    const { project, match, updateTableField } = this.props
    const categoryOptions = [...new Set(
      project.variantTagTypes.map(type => type.category).filter(category => category),
    )]

    const isCategory = categoryOptions.includes(newTag)
    updateTableField('categoryFilter')(isCategory ? newTag : null)
    return getSavedVariantsLinkPath({
      projectGuid: project.projectGuid,
      analysisGroupGuid: match.params.analysisGroupGuid,
      tag: !isCategory && newTag !== SHOW_ALL && newTag,
      familyGuid: match.params.familyGuid,
    })
  }

  loadVariants = (newParams) => {
    const { analysisGroupFamilyGuids, match, loadProjectSavedVariants, updateTableField } = this.props
    const { familyGuid, variantGuid, analysisGroupGuid } = match.params

    const isInitialLoad = match.params === newParams
    const hasUpdatedFamilies = newParams.familyGuid !== familyGuid ||
      newParams.analysisGroupGuid !== analysisGroupGuid ||
      newParams.variantGuid !== variantGuid

    const familyGuids = newParams.familyGuid ? [newParams.familyGuid] : analysisGroupFamilyGuids

    updateTableField('page')(1)
    if (isInitialLoad || hasUpdatedFamilies) {
      loadProjectSavedVariants({ familyGuids, ...newParams })
    }
  }

  tagOptions = () => {
    const { project, match } = this.props
    let currCategory = null
    return (project.variantTagTypes || []).reduce((acc, vtt) => {
      if (vtt.category !== currCategory) {
        currCategory = vtt.category
        if (vtt.category) {
          acc.push({
            key: vtt.category,
            text: vtt.category,
            value: vtt.category,
          })
        }
      }
      acc.push({
        value: vtt.name,
        text: vtt.name,
        key: vtt.name,
        label: { empty: true, circular: true, style: { backgroundColor: vtt.color } },
      })
      return acc
    }, [{
      value: SHOW_ALL,
      text: 'All Saved',
      content: (
        <LabelLink
          to={getSavedVariantsLinkPath({
            projectGuid: project.projectGuid,
            analysisGroupGuid: match.params.analysisGroupGuid,
            familyGuid: match.params.familyGuid,
          })}
        >
          All Saved
        </LabelLink>
      ),
      key: 'all',
    }])
  }

  tableSummary = ({ hideExcluded, hideReviewOnly }) => {
    const { project, tagTypeCounts, match } = this.props
    let excludeItems
    if (hideExcluded) {
      excludeItems = hideReviewOnly ? EXCLUDED_AND_REVIEW_TAGS : EXCLUDED_TAGS
    } else if (hideReviewOnly) {
      excludeItems = REVIEW_TAGS
    }
    return (
      <Grid.Row>
        <Grid.Column width={16}>
          <VariantTagTypeBar
            height={30}
            projectGuid={project.projectGuid}
            familyGuid={match.params.familyGuid}
            analysisGroupGuid={match.params.analysisGroupGuid}
            tagTypeCounts={tagTypeCounts}
            tagTypes={project.variantTagTypes}
            excludeItems={excludeItems}
          />
        </Grid.Column>
      </Grid.Row>
    )
  }

  render() {
    const { project, analysisGroupFamilyGuids, loadProjectSavedVariants, categoryFilter, ...props } = this.props
    const { familyGuid, tag, variantGuid } = props.match.params
    const appliedTagCategoryFilter = tag || (variantGuid ? null : (categoryFilter || SHOW_ALL))

    return (
      <SavedVariants
        tagOptions={this.tagOptions()}
        filters={appliedTagCategoryFilter === DISCOVERY_CATEGORY_NAME ? FILTER_FIELDS : NON_DISCOVERY_FILTER_FIELDS}
        selectedTag={appliedTagCategoryFilter}
        additionalFilter={
          (project.canEdit && familyGuid) ? <LinkSavedVariants familyGuid={familyGuid} {...props} /> : null
        }
        getUpdateTagUrl={this.getUpdateTagUrl}
        loadVariants={this.loadVariants}
        project={project}
        tableSummaryComponent={this.tableSummary}
        {...props}
      />
    )
  }

}

const mapStateToProps = (state, ownProps) => ({
  project: getCurrentProject(state),
  analysisGroupFamilyGuids: getCurrentAnalysisGroupFamilyGuids(state, ownProps),
  tagTypeCounts: ownProps.match.params.familyGuid ?
    getSavedVariantTagTypeCountsByFamily(state)[ownProps.match.params.familyGuid] :
    getSavedVariantTagTypeCounts(state, ownProps),
  categoryFilter: getSavedVariantTableState(state)?.categoryFilter,
})

const mapDispatchToProps = dispatch => ({
  updateTableField: field => (value) => {
    dispatch(updateSavedVariantTable({ [field]: value }))
  },
  loadProjectSavedVariants: (data) => {
    dispatch(loadSavedVariants(data))
  },
})

const ProjectSavedVariants = connect(mapStateToProps, mapDispatchToProps)(BaseProjectSavedVariants)

const RoutedSavedVariants = ({ match }) => (
  <Switch>
    <Route path={`${match.url}/variant/:variantGuid`} component={ProjectSavedVariants} />
    <Route path={`${match.url}/family/:familyGuid/:tag?`} component={ProjectSavedVariants} />
    <Route path={`${match.url}/analysis_group/:analysisGroupGuid/:tag?`} component={ProjectSavedVariants} />
    <Route path={`${match.url}/:tag?`} component={ProjectSavedVariants} />
  </Switch>
)

RoutedSavedVariants.propTypes = {
  match: PropTypes.object,
}

export default RoutedSavedVariants
