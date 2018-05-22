import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Loader, Grid, Pagination } from 'semantic-ui-react'
import styled from 'styled-components'

import VariantTagTypeBar from 'shared/components/graph/VariantTagTypeBar'
import Variants from 'shared/components/panel/variants/Variants'
import { Dropdown, InlineToggle } from 'shared/components/form/Inputs'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { HorizontalSpacer } from 'shared/components/Spacers'
import { loadProjectVariants, updateSavedVariantTable } from '../reducers'
import {
  getProject, getProjectSavedVariantsIsLoading, getProjectSavedVariants, getVisibleSortedProjectSavedVariants,
  getFilteredProjectSavedVariants, getSavedVariantTableState, getSavedVariantVisibleIndices, getSavedVariantTotalPages,
} from '../selectors'
import { VARIANT_SORT_OPTONS } from '../constants'


const BASE_CATEGORY_FILTER_FIELD = {
  name: 'categoryFilter',
  component: Dropdown,
  inline: true,
  selection: false,
  fluid: false,
  label: 'Show category:',
}

const FILTER_FIELDS = [
  {
    name: 'sortOrder',
    component: Dropdown,
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
  .form {
    padding-bottom: 20px;
  }
  
  .field.inline {
    padding-left: 20px;
  }
`


class SavedVariants extends React.Component {

  static propTypes = {
    match: PropTypes.object,
    project: PropTypes.object,
    loading: PropTypes.bool,
    savedVariants: PropTypes.array,
    totalVariantsCount: PropTypes.number,
    filteredVariantsCount: PropTypes.number,
    tableState: PropTypes.object,
    firstRecordIndex: PropTypes.number,
    totalPages: PropTypes.number,
    loadProjectVariants: PropTypes.func,
    updateSavedVariantTable: PropTypes.func,
    updateSavedVariantPage: PropTypes.func,
  }

  constructor(props) {
    super(props)

    props.loadProjectVariants(props.match.params.familyGuid)

    this.categoryOptions = [...new Set(
      this.props.project.variantTagTypes.map(type => type.category).filter(category => category),
    )].map((category) => { return { value: category } })
  }

  componentWillReceiveProps(nextProps) {
    if (nextProps.match.params.familyGuid !== this.props.match.params.familyGuid) {
      this.props.loadProjectVariants(nextProps.match.params.familyGuid)
      this.props.updateSavedVariantTable() // resets the page
    } else if (nextProps.match.params.tag !== this.props.match.params.tag) {
      this.props.updateSavedVariantTable() // resets the page
    }
  }

  render() {
    const { familyGuid, tag } = this.props.match.params
    const filterFields = (this.categoryOptions.length && !tag) ?
      [{ ...BASE_CATEGORY_FILTER_FIELD, options: [{ value: 'ALL', text: 'All' }, ...this.categoryOptions] }].concat(FILTER_FIELDS) :
      FILTER_FIELDS

    return (
      <Grid>
        <Grid.Row>
          <Grid.Column width={16}>
            <VariantTagTypeBar height={30} project={this.props.project} familyGuid={familyGuid} />
          </Grid.Column>
        </Grid.Row>
        {!this.props.loading &&
          <Grid.Row>
            <Grid.Column width={8}>
              Showing {this.props.firstRecordIndex + 1}-
              {this.props.firstRecordIndex + this.props.savedVariants.length} of {this.props.filteredVariantsCount}
              {tag && <b>{` "${tag}"`}</b>} variants ({this.props.totalVariantsCount} total)
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
            </InlineFormColumn>
          </Grid.Row>
        }
        <Grid.Row>
          <Grid.Column width={16}>
            {this.props.loading ? <Loader inline="centered" active /> : <Variants variants={this.props.savedVariants} />}
          </Grid.Column>
        </Grid.Row>
      </Grid>
    )
  }
}

const mapStateToProps = (state, ownProps) => ({
  project: getProject(state),
  loading: getProjectSavedVariantsIsLoading(state),
  savedVariants: getVisibleSortedProjectSavedVariants(state, ownProps),
  totalVariantsCount: getProjectSavedVariants(state, ownProps).length,
  filteredVariantsCount: getFilteredProjectSavedVariants(state, ownProps).length,
  tableState: getSavedVariantTableState(state, ownProps),
  firstRecordIndex: getSavedVariantVisibleIndices(state, ownProps)[0],
  totalPages: getSavedVariantTotalPages(state, ownProps),
})

const mapDispatchToProps = {
  loadProjectVariants,
  updateSavedVariantTable: updates => updateSavedVariantTable({ ...updates, currentPage: 1 }),
  updateSavedVariantPage: (e, data) => updateSavedVariantTable({ currentPage: data.activePage }),
}

export default connect(mapStateToProps, mapDispatchToProps)(SavedVariants)

