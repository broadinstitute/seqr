import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Loader, Grid, Pagination, Dropdown } from 'semantic-ui-react'
import { Link } from 'react-router-dom'
import styled from 'styled-components'

import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import VariantTagTypeBar from 'shared/components/graph/VariantTagTypeBar'
import Variants from 'shared/components/panel/variants/Variants'
import { Dropdown as DropdownInput, InlineToggle } from 'shared/components/form/Inputs'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { HorizontalSpacer } from 'shared/components/Spacers'
import { toSnakecase } from 'shared/utils/stringUtils'
import { loadProjectVariants, updateSavedVariantTable } from '../reducers'
import {
  getProject, getProjectSavedVariantsIsLoading, getProjectSavedVariants, getVisibleSortedProjectSavedVariants,
  getFilteredProjectSavedVariants, getSavedVariantTableState, getSavedVariantVisibleIndices, getSavedVariantTotalPages,
  getSavedVariantExportConfig,
} from '../selectors'
import { VARIANT_SORT_OPTONS } from '../constants'

const ALL_FILTER = 'ALL'

const FILTER_FIELDS = [
  {
    name: 'sortOrder',
    component: DropdownInput,
    inline: true,
    selection: false,
    fluid: false,
    label: 'Sort By:',
    options: VARIANT_SORT_OPTONS,
  },
  {
    name: 'hideExcluded',
    component: InlineToggle,
    label: 'Hide Excluded',
    labelHelp: 'Remove all variants tagged with the "Excluded" tag from the results',
  },
  {
    name: 'hideReviewOnly',
    component: InlineToggle,
    label: 'Hide Review Only',
    labelHelp: 'Remove all variants tagged with only the "Review" tag from the results',
  },
  {
    name: 'recordsPerPage',
    component: DropdownInput,
    inline: true,
    selection: false,
    fluid: false,
    label: 'Variants Per Page:',
    options: [{ value: 10 }, { value: 25 }, { value: 50 }, { value: 100 }],
  },
]

const InlineFormRow = styled(Grid.Row)`
  font-size: 1.1em;
  
  .ui.form {
    display: inline-block;
  }
  
  .field.inline {
    padding-right: 25px;
    
    label {
      font-size: 1.1em !important;
    }
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

class SavedVariants extends React.Component {

  static propTypes = {
    match: PropTypes.object,
    history: PropTypes.object,
    project: PropTypes.object,
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
    updateSavedVariantPage: PropTypes.func,
  }

  constructor(props) {
    super(props)

    props.loadProjectVariants(props.match.params.familyGuid, props.match.params.variantGuid)

    this.categoryOptions = [...new Set(
      this.props.project.variantTagTypes.map(type => type.category).filter(category => category),
    )]
  }

  componentWillReceiveProps(nextProps) {
    const { familyGuid: nextFamilyGuid, variantGuid: nextVariantGuid, tag: nextTag } = nextProps.match.params
    const { familyGuid, variantGuid, tag } = this.props.match.params
    if (nextFamilyGuid !== familyGuid || nextVariantGuid !== variantGuid) {
      this.props.loadProjectVariants(nextFamilyGuid, nextVariantGuid)
      this.props.updateSavedVariantTable() // resets the page
    } else if (nextTag !== tag) {
      this.props.updateSavedVariantTable() // resets the page
    }
  }

  navigateToTag = (e, data) => {
    const { familyGuid } = this.props.match.params
    const isCategory = this.categoryOptions.includes(data.value)
    const urlPath = `/project/${this.props.project.projectGuid}/saved_variants/${familyGuid ? `family/${familyGuid}/` : ''}`
    const tag = data.value === ALL_FILTER ? '' : data.value
    this.props.updateSavedVariantTable({ categoryFilter: isCategory ? data.value : null })
    this.props.history.push(`${urlPath}${isCategory ? '' : tag}`)
  }

  render() {
    const { familyGuid, variantGuid, tag } = this.props.match.params

    const familyId = familyGuid && familyGuid.split(/_(.+)/)[1]
    const exports = [{
      name: `${tag || toSnakecase(this.props.tableState.categoryFilter || 'all')} Variants ${familyId ? `in Family ${familyId}` : ''}`,
      data: {
        filename: `saved_${tag || this.props.tableState.categoryFilter || 'all'}_variants_${this.props.project.name}${familyId ? `_family_${familyId}` : ''}`.replace(/ /g, '-').toLowerCase(),
        ...this.props.variantExportConfig,
      },
    }]

    let currCategory = null
    const tagOptions = [
      {
        value: ALL_FILTER,
        text: 'All Saved',
        content: <LabelLink to={`/project/${this.props.project.projectGuid}/saved_variants/${familyGuid ? `family/${familyGuid}/` : ''}`}>All Saved</LabelLink>,
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
          // content: <LabelLink to={`/project/${this.props.project.projectGuid}/saved_variants/${familyGuid ? `family/${familyGuid}/` : ''}${vtt.name}`}>{vtt.name}</LabelLink>,
          key: vtt.name,
          label: { empty: true, circular: true, style: { backgroundColor: vtt.color } },
        })
        return acc
      }, []),
    ]

    const allShown = this.props.variantsToDisplay.length === this.props.totalVariantsCount
    let shownSummary
    if (allShown) {
      shownSummary = this.props.variantsToDisplay.length > 0 ? 'all' : ''
    }
    else {
      shownSummary = `${this.props.variantsToDisplay.length > 0 ? this.props.firstRecordIndex + 1 : 0}-${this.props.firstRecordIndex + this.props.variantsToDisplay.length} of`
    }
    return (
      <Grid>
        <Grid.Row>
          <Grid.Column width={16}>
            <VariantTagTypeBar
              height={30}
              project={this.props.project}
              familyGuid={familyGuid}
              hideExcluded={this.props.tableState.hideExcluded}
              hideReviewOnly={this.props.tableState.hideReviewOnly}
            />
          </Grid.Column>
        </Grid.Row>
        {!this.props.loading &&
          <InlineFormRow>
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
                  fields={FILTER_FIELDS}
                />
              }
              <HorizontalSpacer width={10} />
              <ExportTableButton downloads={exports} />
              {this.props.totalPages > 1 &&
                <Pagination
                  activePage={this.props.tableState.currentPage || 1}
                  totalPages={this.props.totalPages}
                  onPageChange={this.props.updateSavedVariantPage}
                  size="mini"
                  siblingRange={0}
                />
              }
            </Grid.Column>
          </InlineFormRow>
        }
        <Grid.Row>
          <Grid.Column width={16}>
            {this.props.loading ? <Loader inline="centered" active /> :
            <Variants variants={this.props.variantsToDisplay} projectGuid={this.props.project.projectGuid} />}
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
})

const mapDispatchToProps = {
  loadProjectVariants,
  updateSavedVariantTable: updates => updateSavedVariantTable({ ...updates, currentPage: 1 }),
  updateSavedVariantPage: (e, data) => updateSavedVariantTable({ currentPage: data.activePage }),
}

export default connect(mapStateToProps, mapDispatchToProps)(SavedVariants)

