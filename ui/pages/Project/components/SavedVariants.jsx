import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Loader, Grid, Dropdown } from 'semantic-ui-react'
import { Route, Switch, Link } from 'react-router-dom'
import styled from 'styled-components'

import { getAnalysisGroupsByGuid } from 'redux/selectors'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import VariantTagTypeBar, { getSavedVariantsLinkPath } from 'shared/components/graph/VariantTagTypeBar'
import Variants from 'shared/components/panel/variants/Variants'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { HorizontalSpacer } from 'shared/components/Spacers'
import { toSnakecase } from 'shared/utils/stringUtils'
import {
  VARIANT_SORT_FIELD,
  VARIANT_HIDE_EXCLUDED_FIELD,
  VARIANT_HIDE_REVIEW_FIELD,
  VARIANT_PER_PAGE_FIELD,
  VARIANT_PAGINATION_FIELD,
} from 'shared/utils/constants'
import { loadProjectVariants, updateSavedVariantTable } from '../reducers'
import {
  getProject, getProjectSavedVariantsIsLoading, getProjectSavedVariants, getVisibleSortedProjectSavedVariants,
  getFilteredProjectSavedVariants, getSavedVariantTableState, getSavedVariantVisibleIndices, getSavedVariantTotalPages,
  getSavedVariantExportConfig,
} from '../selectors'

const ALL_FILTER = 'ALL'

const FILTER_FIELDS = [
  VARIANT_SORT_FIELD,
  VARIANT_HIDE_EXCLUDED_FIELD,
  VARIANT_HIDE_REVIEW_FIELD,
  VARIANT_PER_PAGE_FIELD,
]

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
    loading: PropTypes.bool,
    variantsToDisplay: PropTypes.array,
    totalVariantsCount: PropTypes.number,
    filteredVariants: PropTypes.array,
    variantExportConfig: PropTypes.object,
    tableState: PropTypes.object,
    firstRecordIndex: PropTypes.number,
    totalPages: PropTypes.number,
    loadProjectVariants: PropTypes.func,
    updateSavedVariantTable: PropTypes.func,
  }

  constructor(props) {
    super(props)

    this.loadVariants(props)

    this.categoryOptions = [...new Set(
      this.props.project.variantTagTypes.map(type => type.category).filter(category => category),
    )]
  }

  componentWillReceiveProps(nextProps) {
    const {
      familyGuid: nextFamilyGuid, analysisGroupGuid: nextAnalysisGroupGuid, variantGuid: nextVariantGuid, tag: nextTag,
    } = nextProps.match.params
    const { familyGuid, variantGuid, analysisGroupGuid, tag } = this.props.match.params
    if (nextFamilyGuid !== familyGuid || nextAnalysisGroupGuid !== analysisGroupGuid || nextVariantGuid !== variantGuid) {
      this.loadVariants(nextProps)
      this.props.updateSavedVariantTable() // resets the page
    } else if (nextTag !== tag) {
      this.props.updateSavedVariantTable() // resets the page
    }
  }

  loadVariants = ({ match, analysisGroup }) => {
    const { familyGuid, variantGuid } = match.params
    const familyGuids = familyGuid ? [familyGuid] : (analysisGroup || {}).familyGuids
    this.props.loadProjectVariants(familyGuids, variantGuid)
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
        filename: toSnakecase(`saved_${tagName}_variants_${this.props.project.name}${familyId ? `_family_${familyId}` : ''}${analsisGroupName ? `_analysis_group_${analsisGroupName}` : ''}`),
        ...this.props.variantExportConfig,
      },
    }]

    let currCategory = null
    const tagOptions = [
      {
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
      },
      ...this.props.project.variantTagTypes.reduce((acc, vtt) => {
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

    const filterFields = this.props.totalPages > 1 ?
      [...FILTER_FIELDS, { ...VARIANT_PAGINATION_FIELD, totalPages: this.props.totalPages }] : FILTER_FIELDS

    const allShown = this.props.variantsToDisplay.length === this.props.totalVariantsCount
    let shownSummary = ''
    if (!allShown) {
      shownSummary = `${this.props.variantsToDisplay.length > 0 ? this.props.firstRecordIndex + 1 : 0}-${this.props.firstRecordIndex + this.props.variantsToDisplay.length} of`
    }
    return (
      <Grid stackable>
        <Grid.Row>
          <Grid.Column width={16}>
            <VariantTagTypeBar
              height={30}
              project={this.props.project}
              analysisGroup={this.props.analysisGroup}
              familyGuid={familyGuid}
              hideExcluded={this.props.tableState.hideExcluded}
              hideReviewOnly={this.props.tableState.hideReviewOnly}
            />
          </Grid.Column>
        </Grid.Row>
        {!this.props.loading &&
          <ControlsRow>
            <Grid.Column width={5}>
              Showing {shownSummary} {this.props.filteredVariants.length}
              &nbsp;&nbsp;
              <Dropdown
                inline
                options={tagOptions}
                value={tag || (variantGuid ? null : (this.props.tableState.categoryFilter || ALL_FILTER))}
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
                  fields={filterFields}
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
  project: getProject(state),
  loading: getProjectSavedVariantsIsLoading(state),
  variantsToDisplay: getVisibleSortedProjectSavedVariants(state, ownProps),
  totalVariantsCount: getProjectSavedVariants(state, ownProps).length,
  filteredVariants: getFilteredProjectSavedVariants(state, ownProps),
  tableState: getSavedVariantTableState(state, ownProps),
  firstRecordIndex: getSavedVariantVisibleIndices(state, ownProps)[0],
  totalPages: getSavedVariantTotalPages(state, ownProps),
  variantExportConfig: getSavedVariantExportConfig(state, ownProps),
  analysisGroup: getAnalysisGroupsByGuid(state)[ownProps.match.params.analysisGroupGuid],
})

const mapDispatchToProps = {
  loadProjectVariants,
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
