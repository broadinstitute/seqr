import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Route, Switch, Link } from 'react-router-dom'
import { Grid } from 'semantic-ui-react'
import styled from 'styled-components'

import { updateSavedVariantTable } from 'redux/rootReducer'
import { getAnalysisGroupsByGuid, getCurrentProject } from 'redux/selectors'
import {
  VARIANT_SORT_FIELD,
  VARIANT_HIDE_EXCLUDED_FIELD,
  VARIANT_HIDE_REVIEW_FIELD,
  VARIANT_HIDE_KNOWN_GENE_FOR_PHENOTYPE_FIELD,
  VARIANT_PER_PAGE_FIELD,
} from 'shared/utils/constants'
import VariantTagTypeBar, { getSavedVariantsLinkPath } from 'shared/components/graph/VariantTagTypeBar'
import SavedVariants from 'shared/components/panel/variants/SavedVariants'

import { loadSavedVariants } from '../reducers'

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

const BaseProjectSavedVariants = ({ project, analysisGroup, loadProjectSavedVariants, ...props }) => {
  const { familyGuid, tag, variantGuid, analysisGroupGuid } = props.match.params

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
    const hasUpdatedTag = newParams.tag !== tag
    const hasUpdatedFamilies = newParams.familyGuid !== familyGuid ||
      newParams.analysisGroupGuid !== analysisGroupGuid ||
      newParams.variantGuid !== variantGuid

    const familyGuids = newParams.familyGuid ? [newParams.familyGuid] : (analysisGroup || {}).familyGuids

    if (hasUpdatedTag || hasUpdatedFamilies) {
      props.updateTable({ page: 1 })
    }
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
      getUpdateTagUrl={getUpdateTagUrl}
      loadVariants={loadVariants}
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
}

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
