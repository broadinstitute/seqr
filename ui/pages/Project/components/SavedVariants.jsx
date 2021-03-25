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
} from 'shared/utils/constants'
import UpdateButton from 'shared/components/buttons/UpdateButton'
import { LargeMultiselect } from 'shared/components/form/Inputs'
import SavedVariants from 'shared/components/panel/variants/SavedVariants'

import { TAG_FORM_FIELD } from '../constants'
import { loadSavedVariants, updateSavedVariantTable } from '../reducers'
import { getCurrentProject, getProjectTagTypeOptions, getTaggedVariantsByFamily } from '../selectors'
import VariantTagTypeBar, { getSavedVariantsLinkPath } from './VariantTagTypeBar'
import SelectSavedVariantsTable, { TAG_COLUMN, VARIANT_POS_COLUMN, GENES_COLUMN } from './SelectSavedVariantsTable'

const ALL_FILTER = 'ALL'

const FILTER_FIELDS = [
  VARIANT_SORT_FIELD,
  VARIANT_HIDE_KNOWN_GENE_FOR_PHENOTYPE_FIELD,
  VARIANT_HIDE_EXCLUDED_FIELD,
  VARIANT_HIDE_REVIEW_FIELD,
  VARIANT_PER_PAGE_FIELD,
]
const NON_DISCOVERY_FILTER_FIELDS = FILTER_FIELDS.filter(({ name }) => name !== 'hideKnownGeneForPhenotype')

const LabelLink = styled(Link)`
  color: black;
  
  &:hover {
    color: black;
  }
`

const BASE_FORM_ID = '-linkVariants'

const mapVariantLinkStateToProps = (state, ownProps) => {
  const familyGuid = ownProps.meta.form.split(BASE_FORM_ID)[0]
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
    // redux form inexplicably updates the value to be a boolean on some focus changes and we should ignore that
    normalize: (val, prevVal) => (typeof val === 'boolean' ? prevVal : val),
    validate: value => (Object.keys(value || {}).length > 1 ? undefined : 'Multiple variants required'),
  },
]

const BaseLinkSavedVariants = ({ familyGuid, onSubmit }) =>
  <UpdateButton
    modalTitle="Link Saved Variants"
    modalId={`${familyGuid}${BASE_FORM_ID}`}
    buttonText="Link Variants"
    editIconName="linkify"
    size="medium"
    formFields={LINK_VARIANT_FIELDS}
    onSubmit={onSubmit}
    showErrorPanel
  />

BaseLinkSavedVariants.propTypes = {
  familyGuid: PropTypes.string,
  onSubmit: PropTypes.func,
}

const mapVariantDispatchToProps = (dispatch, { familyGuid }) => {
  return {
    onSubmit: (values) => {
      const variantGuids = Object.keys(values.variantGuids).filter(
        variantGuid => values.variantGuids[variantGuid]).join(',')
      dispatch(updateVariantTags({ ...values, familyGuid, variantGuids }))
    },
  }
}

const LinkSavedVariants = connect(null, mapVariantDispatchToProps)(BaseLinkSavedVariants)

const BaseProjectSavedVariants = React.memo(({ project, analysisGroup, loadProjectSavedVariants, ...props }) => {
  const { familyGuid, variantGuid, analysisGroupGuid } = props.match.params

  const categoryOptions = [...new Set(
    project.variantTagTypes.map(type => type.category).filter(category => category),
  )]

  const getUpdateTagUrl = (newTag) => {
    const isCategory = categoryOptions.includes(newTag)
    props.updateTable({ categoryFilter: isCategory ? newTag : null })
    return getSavedVariantsLinkPath({
      project,
      analysisGroup,
      tag: !isCategory && newTag !== ALL_FILTER && newTag,
      familyGuid,
    })
  }

  const loadVariants = (newParams) => {
    const isInitialLoad = props.match.params === newParams
    const hasUpdatedFamilies = newParams.familyGuid !== familyGuid ||
      newParams.analysisGroupGuid !== analysisGroupGuid ||
      newParams.variantGuid !== variantGuid

    const familyGuids = newParams.familyGuid ? [newParams.familyGuid] : (analysisGroup || {}).familyGuids

    props.updateTable({ page: 1 })
    if (isInitialLoad || hasUpdatedFamilies) {
      loadProjectSavedVariants({ familyGuids, ...newParams })
    }
  }

  let currCategory = null
  const tagOptions =
    project.variantTagTypes.reduce((acc, vtt) => {
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
          to={getSavedVariantsLinkPath({ project, analysisGroup, familyGuid })}
        >
          All Saved
        </LabelLink>
      ),
      key: 'all',
    }])

  return (
    <SavedVariants
      tagOptions={tagOptions}
      filters={NON_DISCOVERY_FILTER_FIELDS}
      discoveryFilters={FILTER_FIELDS}
      additionalFilter={(project.canEdit && familyGuid) ? <LinkSavedVariants familyGuid={familyGuid} {...props} /> : null}
      getUpdateTagUrl={getUpdateTagUrl}
      loadVariants={loadVariants}
      project={project}
      tableSummaryComponent={
        summaryProps =>
          <Grid.Row>
            <Grid.Column width={16}>
              <VariantTagTypeBar
                height={30}
                project={project}
                analysisGroup={analysisGroup}
                {...summaryProps}
              />
            </Grid.Column>
          </Grid.Row>
      }
      {...props}
    />
  )
})

BaseProjectSavedVariants.propTypes = {
  match: PropTypes.object,
  project: PropTypes.object,
  analysisGroup: PropTypes.object,
  updateTable: PropTypes.func,
  loadProjectSavedVariants: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  project: getCurrentProject(state),
  analysisGroup: getAnalysisGroupsByGuid(state)[ownProps.match.params.analysisGroupGuid],
})

const mapDispatchToProps = {
  updateTable: updateSavedVariantTable,
  loadProjectSavedVariants: loadSavedVariants,
}

const ProjectSavedVariants = connect(mapStateToProps, mapDispatchToProps)(BaseProjectSavedVariants)

const RoutedSavedVariants = ({ match }) =>
  <Switch>
    <Route path={`${match.url}/variant/:variantGuid`} component={ProjectSavedVariants} />
    <Route path={`${match.url}/family/:familyGuid/:tag?`} component={ProjectSavedVariants} />
    <Route path={`${match.url}/analysis_group/:analysisGroupGuid/:tag?`} component={ProjectSavedVariants} />
    <Route path={`${match.url}/:tag?`} component={ProjectSavedVariants} />
  </Switch>

RoutedSavedVariants.propTypes = {
  match: PropTypes.object,
}

export default RoutedSavedVariants
