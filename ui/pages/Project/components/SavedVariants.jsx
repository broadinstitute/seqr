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
import { titlecase } from 'shared/utils/stringUtils'
import { loadProjectVariants, updateSavedVariantTable } from '../reducers'
import {
  getProject, getProjectSavedVariantsIsLoading, getProjectSavedVariants, getVisibleSortedProjectSavedVariants,
  getFilteredProjectSavedVariants, getSavedVariantTableState, getSavedVariantVisibleIndices, getSavedVariantTotalPages,
  getSavedVariantExportConfig,
} from '../selectors'
import { VARIANT_SORT_OPTONS } from '../constants'


const BASE_CATEGORY_FILTER_FIELD = {
  name: 'categoryFilter',
  component: DropdownInput,
  inline: true,
  selection: false,
  fluid: false,
  label: 'Show category:',
}

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
  },
]

const InlineFormColumn = styled(Grid.Column)`
  .ui.form {
    display: inline-block;
  }
  
  .field.inline {
    padding-left: 20px;
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
    )].map((category) => { return { value: category } })
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

  render() {
    const { familyGuid, variantGuid, tag } = this.props.match.params
    const filterFields = (this.categoryOptions.length && !tag) ?
      [{ ...BASE_CATEGORY_FILTER_FIELD, options: [{ value: 'ALL', text: 'All' }, ...this.categoryOptions] }].concat(FILTER_FIELDS) :
      FILTER_FIELDS

    const familyId = familyGuid && familyGuid.split(/_(.+)/)[1]
    const exports = [{
      name: `${tag || titlecase(this.props.tableState.categoryFilter)} Variants ${familyId ? `in Family ${familyId}` : ''}`,
      data: {
        filename: `saved_${tag || this.props.tableState.categoryFilter}_variants_${this.props.project.name}${familyId ? `_family_${familyId}` : ''}`.replace(/ /g, '-').toLowerCase(),
        ...this.props.variantExportConfig,
      },
    }]

    const tagOptions = [
      {
        value: 'ALL',
        text: <LabelLink to={`/project/${this.props.project.projectGuid}/saved_variants/${familyGuid ? `family/${familyGuid}/` : ''}`}>All Saved</LabelLink>,
        key: 'all',
      },
      ...this.props.project.variantTagTypes.map(vtt => ({
        value: vtt.name,
        text: <LabelLink to={`/project/${this.props.project.projectGuid}/saved_variants/${familyGuid ? `family/${familyGuid}/` : ''}${vtt.name}`}>{vtt.name}</LabelLink>,
        key: vtt.name,
        label: { empty: true, circular: true, style: { backgroundColor: vtt.color } },
      })),
    ]

    const allShown = this.props.variantsToDisplay.length === this.props.totalVariantsCount
    const shownSummary = allShown ? 'all' :
      `${this.props.firstRecordIndex + 1}-${this.props.firstRecordIndex + this.props.variantsToDisplay.length} of`
    return (
      <Grid>
        {!variantGuid &&
          <Grid.Row>
            <Grid.Column width={16}>
              <VariantTagTypeBar height={30} project={this.props.project} familyGuid={familyGuid} />
            </Grid.Column>
          </Grid.Row>
        }
        {!this.props.loading && !variantGuid &&
          <Grid.Row>
            <Grid.Column width={8}>
              Showing {shownSummary} {this.props.filteredVariants.length}
              &nbsp;&nbsp;<Dropdown inline options={tagOptions} value={tag || 'ALL'} />
              &nbsp;variants {!allShown && `(${this.props.totalVariantsCount} total)`}
              <HorizontalSpacer width={20} />
              <Pagination
                activePage={this.props.tableState.currentPage || 1}
                totalPages={this.props.totalPages}
                onPageChange={this.props.updateSavedVariantPage}
                size="mini"
              />
            </Grid.Column>
            <InlineFormColumn width={8} floated="right" textAlign="right">
              <ReduxFormWrapper
                onSubmit={this.props.updateSavedVariantTable}
                form="editSavedVariantTable"
                initialValues={this.props.tableState}
                closeOnSuccess={false}
                submitOnChange
                fields={filterFields}
              />
              <HorizontalSpacer width={10} />
              <ExportTableButton downloads={exports} />
            </InlineFormColumn>
          </Grid.Row>
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

