import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Route, Switch, Link } from 'react-router-dom'
import { Grid } from 'semantic-ui-react'
import styled from 'styled-components'

import { updateVariantTags } from 'redux/rootReducer'
import { getAnalysisGroupsByGuid } from 'redux/selectors'
import {
  VARIANT_SORT_FIELD,
  VARIANT_HIDE_EXCLUDED_FIELD,
  VARIANT_HIDE_REVIEW_FIELD,
  VARIANT_HIDE_KNOWN_GENE_FOR_PHENOTYPE_FIELD,
  VARIANT_PER_PAGE_FIELD,
  EXCLUDED_TAG_NAME,
  REVIEW_TAG_NAME,
} from 'shared/utils/constants'
import UpdateButton from 'shared/components/buttons/UpdateButton'
import { LargeMultiselect, Dropdown } from 'shared/components/form/Inputs'
import SavedVariants from 'shared/components/panel/variants/SavedVariants'

import { TAG_FORM_FIELD } from '../constants'
import { loadSavedVariants, updateSavedVariantTable } from '../reducers'
import {
  getCurrentProject, getProjectTagTypeOptions, getTaggedVariantsByFamily, getProjectVariantSavedByOptions,
  getSavedVariantTagTypeCounts, getSavedVariantTagTypeCountsByFamily,
} from '../selectors'
import VariantTagTypeBar, { getSavedVariantsLinkPath } from './VariantTagTypeBar'
import SelectSavedVariantsTable, { TAG_COLUMN, VARIANT_POS_COLUMN, GENES_COLUMN } from './SelectSavedVariantsTable'

const LabelLink = styled(Link)`
  color: black;
  
  &:hover {
    color: black;
  }
`

const ALL_FILTER = 'ALL'

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
    validate: value => (Object.keys(value || {}).length > 1 ? undefined : 'Multiple variants required'),
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
    analysisGroup: PropTypes.object,
    tagTypeCounts: PropTypes.object,
    updateTableField: PropTypes.func,
    loadProjectSavedVariants: PropTypes.func,
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
      tag: !isCategory && newTag !== ALL_FILTER && newTag,
      familyGuid: match.params.familyGuid,
    })
  }

  loadVariants = (newParams) => {
    const { analysisGroup, match, loadProjectSavedVariants, updateTableField } = this.props
    const { familyGuid, variantGuid, analysisGroupGuid } = match.params

    const isInitialLoad = match.params === newParams
    const hasUpdatedFamilies = newParams.familyGuid !== familyGuid ||
      newParams.analysisGroupGuid !== analysisGroupGuid ||
      newParams.variantGuid !== variantGuid

    const familyGuids = newParams.familyGuid ? [newParams.familyGuid] : (analysisGroup || {}).familyGuids

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
      value: ALL_FILTER,
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
    const { project, analysisGroup, loadProjectSavedVariants, ...props } = this.props
    const { familyGuid } = props.match.params

    return (
      <SavedVariants
        tagOptions={this.tagOptions()}
        filters={NON_DISCOVERY_FILTER_FIELDS}
        discoveryFilters={FILTER_FIELDS}
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
  analysisGroup: getAnalysisGroupsByGuid(state)[ownProps.match.params.analysisGroupGuid],
  tagTypeCounts: ownProps.match.params.familyGuid ?
    getSavedVariantTagTypeCountsByFamily(state)[ownProps.match.params.familyGuid] :
    getSavedVariantTagTypeCounts(state, ownProps),
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
