import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Loader, Grid, Dropdown } from 'semantic-ui-react'
import { Route, Switch, Link } from 'react-router-dom'
import styled from 'styled-components'

import { loadSavedVariants, updateSavedVariantTable } from 'redux/rootReducer'
import { getAnalysisGroupsByGuid, getCurrentProject, getSavedVariantsIsLoading, getSelectedSavedVariants,
  getVisibleSortedSavedVariants, getFilteredSavedVariants, getSavedVariantTableState,
  getSavedVariantVisibleIndices, getSavedVariantTotalPages, getSavedVariantExportConfig } from 'redux/selectors'
import {
  KNOWN_GENE_FOR_PHENOTYPE_TAG_NAME,
  DISCOVERY_CATEGORY_NAME,
  VARIANT_SORT_FIELD,
  VARIANT_HIDE_EXCLUDED_FIELD,
  VARIANT_HIDE_REVIEW_FIELD,
  VARIANT_HIDE_KNOWN_GENE_FOR_PHENOTYPE_FIELD,
  VARIANT_PER_PAGE_FIELD,
  VARIANT_PAGINATION_FIELD,
  VARIANT_GENE_FIELD,
  VARIANT_TAGGED_DATE_FIELD,
} from 'shared/utils/constants'
import { toSnakecase } from 'shared/utils/stringUtils'

import ExportTableButton from '../../buttons/export-table/ExportTableButton'
import VariantTagTypeBar, { getSavedVariantsLinkPath } from '../../graph/VariantTagTypeBar'
import ReduxFormWrapper from '../../form/ReduxFormWrapper'
import { HorizontalSpacer } from '../../Spacers'
import Variants from './Variants'

const ALL_FILTER = 'ALL'

const NO_PROJECT_FILTER_FIELDS = [
  VARIANT_GENE_FIELD,
  VARIANT_TAGGED_DATE_FIELD,
  VARIANT_SORT_FIELD,
  VARIANT_PER_PAGE_FIELD,
]
const FILTER_FIELDS = [
  VARIANT_SORT_FIELD,
  VARIANT_HIDE_KNOWN_GENE_FOR_PHENOTYPE_FIELD,
  VARIANT_HIDE_EXCLUDED_FIELD,
  VARIANT_HIDE_REVIEW_FIELD,
  VARIANT_PER_PAGE_FIELD,
]
const NON_DISCOVERY_FILTER_FIELDS = FILTER_FIELDS.filter(({ name }) => name !== 'hideKnownGeneForPhenotype')

const TAG_TYPES = [
  'Tier 1 - Novel gene and phenotype',
  'Tier 1 - Novel gene for known phenotype',
  'Tier 1 - Phenotype expansion',
  'Tier 1 - Phenotype not delineated',
  'Tier 1 - Novel mode of inheritance',
  'Tier 1 - Known gene, new phenotype',
  'Tier 2 - Novel gene and phenotype',
  'Tier 2 - Novel gene for known phenotype',
  'Tier 2 - Phenotype expansion',
  'Tier 2 - Phenotype not delineated',
  'Tier 2 - Known gene, new phenotype',
  KNOWN_GENE_FOR_PHENOTYPE_TAG_NAME,
  'Send for Sanger validation',
  'Sanger validated',
  'Sanger did not confirm',
  'Confident AR one hit',
  'MatchBox (MME)',
  'Submit to Clinvar',
  'Share with KOMP',
].map(name => ({ name, color: 'white' }))

const ControlsRow = styled(Grid.Row)`
  font-size: 1.1em;
  
  label {
    font-size: 1.1em !important;
  }
  
  .pagination {
    margin-top: 10px !important;
  }
`

const LabelLink = styled(Link)`
  color: black;
  
  &:hover {
    color: black;
  }
`

class BaseSavedVariants extends React.Component {

  static propTypes = {
    match: PropTypes.object,
    history: PropTypes.object,
    project: PropTypes.object,
    analysisGroup: PropTypes.object,
    variantTagTypes: PropTypes.array,
    loading: PropTypes.bool,
    variantsToDisplay: PropTypes.array,
    totalVariantsCount: PropTypes.number,
    filteredVariants: PropTypes.array,
    variantExportConfig: PropTypes.object,
    tableState: PropTypes.object,
    firstRecordIndex: PropTypes.number,
    totalPages: PropTypes.number,
    loadSavedVariants: PropTypes.func,
    updateSavedVariantTable: PropTypes.func,
  }

  constructor(props) {
    super(props)

    this.loadVariants(props)

    this.categoryOptions = this.props.project ? [...new Set(
      this.props.project.variantTagTypes.map(type => type.category).filter(category => category),
    )] : []
  }

  componentWillReceiveProps(nextProps) {
    const {
      familyGuid: nextFamilyGuid, analysisGroupGuid: nextAnalysisGroupGuid, variantGuid: nextVariantGuid, tag: nextTag,
    } = nextProps.match.params
    const { familyGuid, variantGuid, analysisGroupGuid, tag } = this.props.match.params
    if (nextFamilyGuid !== familyGuid || nextAnalysisGroupGuid !== analysisGroupGuid || nextVariantGuid !== variantGuid) {
      this.loadVariants(nextProps)
      this.props.updateSavedVariantTable({ page: 1 })
    } else if (nextTag !== tag) {
      this.props.updateSavedVariantTable({ page: 1 })
      if (!this.props.project) {
        this.loadVariants(nextProps)
      }
    }
  }

  loadVariants = ({ match, analysisGroup }) => {
    const { familyGuid, variantGuid, tag } = match.params
    const familyGuids = familyGuid ? [familyGuid] : (analysisGroup || {}).familyGuids
    this.props.loadSavedVariants(familyGuids, variantGuid, tag)
  }


  navigateToTag = (e, data) => {
    const { familyGuid } = this.props.match.params
    const isCategory = this.categoryOptions.includes(data.value)
    const urlPath = getSavedVariantsLinkPath({
      project: this.props.project,
      analysisGroup: this.props.analysisGroup,
      tag: !isCategory && data.value !== ALL_FILTER && data.value,
      familyGuid,
    })
    this.props.updateSavedVariantTable({ categoryFilter: isCategory ? data.value : null })
    this.props.history.push(urlPath)
  }

  render() {
    const { familyGuid, variantGuid, tag } = this.props.match.params

    const familyId = familyGuid && familyGuid.split(/_(.+)/)[1]
    const analsisGroupName = (this.props.analysisGroup || {}).name
    const tagName = tag || this.props.tableState.categoryFilter || 'All'
    const exports = [{
      name: `${tagName} Variants${familyId ? ` in Family ${familyId}` : ''}${analsisGroupName ? ` in Analysis Group ${analsisGroupName}` : ''}`,
      data: {
        filename: toSnakecase(`saved_${tagName}_variants_${(this.props.project || {}).name}${familyId ? `_family_${familyId}` : ''}${analsisGroupName ? `_analysis_group_${analsisGroupName}` : ''}`),
        ...this.props.variantExportConfig,
      },
    }]

    let currCategory = null
    const tagOptions = [
      ...(this.props.project ? this.props.project.variantTagTypes : TAG_TYPES).reduce((acc, vtt) => {
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
      }, []),
    ]
    if (this.props.project) {
      tagOptions.unshift({
        value: ALL_FILTER,
        text: 'All Saved',
        content: (
          <LabelLink
            to={getSavedVariantsLinkPath({ project: this.props.project, analysisGroup: this.props.analysisGroup, familyGuid })}
          >
            All Saved
          </LabelLink>
        ),
        key: 'all',
      })
    }

    const appliedTagCategoryFilter = tag || (variantGuid ? null : (this.props.tableState.categoryFilter || ALL_FILTER))

    let filters
    if (this.props.project) {
      filters = appliedTagCategoryFilter === DISCOVERY_CATEGORY_NAME ? FILTER_FIELDS : NON_DISCOVERY_FILTER_FIELDS
    } else {
      filters = NO_PROJECT_FILTER_FIELDS
    }

    if (this.props.totalPages > 1) {
      filters = filters.concat({ ...VARIANT_PAGINATION_FIELD, totalPages: this.props.totalPages })
    }

    const allShown = this.props.variantsToDisplay.length === this.props.totalVariantsCount
    let shownSummary = ''
    if (!allShown) {
      shownSummary = `${this.props.variantsToDisplay.length > 0 ? this.props.firstRecordIndex + 1 : 0}-${this.props.firstRecordIndex + this.props.variantsToDisplay.length} of`
    }
    return (
      <Grid stackable>
        {this.props.project &&
          <Grid.Row>
            <Grid.Column width={16}>
              <VariantTagTypeBar
                height={30}
                project={this.props.project}
                analysisGroup={this.props.analysisGroup}
                familyGuid={variantGuid ? ((this.props.variantsToDisplay[0] || {}).familyGuids || [])[0] : familyGuid}
                hideExcluded={this.props.tableState.hideExcluded}
                hideReviewOnly={this.props.tableState.hideReviewOnly}
              />
            </Grid.Column>
          </Grid.Row>
        }
        {!this.props.loading &&
          <ControlsRow>
            <Grid.Column width={5}>
              Showing {shownSummary} {this.props.filteredVariants.length}
              &nbsp;&nbsp;
              <Dropdown
                inline
                options={tagOptions}
                value={appliedTagCategoryFilter}
                onChange={this.navigateToTag}
              />
              &nbsp;variants {!allShown && `(${this.props.totalVariantsCount} total)`}

            </Grid.Column>
            <Grid.Column width={11} floated="right" textAlign="right">
              {!variantGuid &&
                <ReduxFormWrapper
                  onSubmit={this.props.updateSavedVariantTable}
                  form="editSavedVariantTable"
                  initialValues={this.props.tableState}
                  closeOnSuccess={false}
                  submitOnChange
                  inline
                  fields={filters}
                />
              }
              <HorizontalSpacer width={10} />
              <ExportTableButton downloads={exports} />
            </Grid.Column>
          </ControlsRow>
        }
        <Grid.Row>
          <Grid.Column width={16}>
            {this.props.loading ? <Loader inline="centered" active /> :
            <Variants variants={this.props.variantsToDisplay} />}
          </Grid.Column>
        </Grid.Row>
      </Grid>
    )
  }
}

const mapStateToProps = (state, ownProps) => ({
  project: getCurrentProject(state),
  loading: getSavedVariantsIsLoading(state),
  variantsToDisplay: getVisibleSortedSavedVariants(state, ownProps),
  totalVariantsCount: getSelectedSavedVariants(state, ownProps).length,
  filteredVariants: getFilteredSavedVariants(state, ownProps),
  tableState: getSavedVariantTableState(state, ownProps),
  firstRecordIndex: getSavedVariantVisibleIndices(state, ownProps)[0],
  totalPages: getSavedVariantTotalPages(state, ownProps),
  variantExportConfig: getSavedVariantExportConfig(state, ownProps),
  analysisGroup: getAnalysisGroupsByGuid(state)[ownProps.match.params.analysisGroupGuid],
})

const mapDispatchToProps = {
  loadSavedVariants,
  updateSavedVariantTable,
}

const SavedVariants = connect(mapStateToProps, mapDispatchToProps)(BaseSavedVariants)

const RoutedSavedVariants = ({ match }) =>
  <Switch>
    <Route path={`${match.url}/variant/:variantGuid`} component={SavedVariants} />
    <Route path={`${match.url}/family/:familyGuid/:tag?`} component={SavedVariants} />
    <Route path={`${match.url}/analysis_group/:analysisGroupGuid/:tag?`} component={SavedVariants} />
    <Route path={`${match.url}/:tag?`} component={SavedVariants} />
  </Switch>

RoutedSavedVariants.propTypes = {
  match: PropTypes.object,
}

export default RoutedSavedVariants
