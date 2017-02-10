import React from 'react'
import { Form, Grid, Table } from 'semantic-ui-react'
import max from 'lodash/max'
import FamilyRow from './FamilyRow'
import IndividualRow from './IndividualRow'
import HorizontalStackedBar from '../../../shared/components/HorizontalStackedBar'

import { SortDirectionToggle, HorizontalOnOffToggle } from '../../../shared/components/form/Toggle'
import { HorizontalSpacer } from '../../../shared/components/Spacers'

const LOCAL_STORAGE_SHOW_DETAILS_KEY = 'CaseReviewTable.showDetails'
const LOCAL_STORAGE_FAMILIES_FILTER_KEY = 'CaseReviewTable.familiesFilter'
const LOCAL_STORAGE_FAMILIES_SORT_ORDER_KEY = 'CaseReviewTable.familiesSortOrder'
const LOCAL_STORAGE_FAMILIES_SORT_DIRECTION_KEY = 'CaseReviewTable.familiesSortDirection'

class CaseReviewTable extends React.Component {

  static propTypes = {
    project: React.PropTypes.object.isRequired,
    familiesByGuid: React.PropTypes.object.isRequired,
    individualsByGuid: React.PropTypes.object.isRequired,
    familyGuidToIndivGuids: React.PropTypes.object.isRequired,
  }

  static SHOW_ALL = 'ALL'
  static SHOW_ACCEPTED = 'ACCEPTED'
  static SHOW_NOT_ACCEPTED = 'NOT_ACCEPTED'
  static SHOW_IN_REVIEW = 'IN_REVIEW'
  static SHOW_UNCERTAIN = 'UNCERTAIN'
  static SHOW_MORE_INFO_NEEDED = 'MORE_INFO_NEEDED'

  static SORT_BY_FAMILY_NAME = 'FAMILY_NAME'
  static SORT_BY_DATE_ADDED = 'DATE_ADDED'
  static SORT_BY_DATE_STATUS_CHANGED = 'STATUS_CHANGED'


  /**
   * Returns a comparator function for sorting families according to one of the SORT_BY_* constants.
   * @params familiesSortOrder {string}
   * @params direction {number}
   * @param familiesByGuid {object}
   * @returns {function(*, *): number}
   */
  static createFamilySortComparator(familiesSortOrder, direction, familiesByGuid, familyGuidToIndivGuids, individualsByGuid) {
    const genericComparison = (a, b) => ((a && b) ? (a < b) - (a > b) : ((a && 1) || -1))

    switch (familiesSortOrder) {
      case CaseReviewTable.SORT_BY_FAMILY_NAME:
        return (a, b) => {
          return -1 * direction * genericComparison(familiesByGuid[a].displayName, familiesByGuid[b].displayName)
        }
      case CaseReviewTable.SORT_BY_DATE_ADDED:
        return (a, b) => {
          a = max(familyGuidToIndivGuids[a].map(i => individualsByGuid[i].createdDate))
          b = max(familyGuidToIndivGuids[b].map(i => individualsByGuid[i].createdDate))
          return direction * genericComparison(a, b)
        }
      case CaseReviewTable.SORT_BY_DATE_STATUS_CHANGED:
        return (a, b) => {
          a = max(familyGuidToIndivGuids[a].map(i => individualsByGuid[i].caseReviewStatusLastModifiedDate))
          b = max(familyGuidToIndivGuids[b].map(i => individualsByGuid[i].caseReviewStatusLastModifiedDate))
          return direction * genericComparison(a, b)
        }
      default:
        return (a, b) => {
          return direction * genericComparison(a, b)
        }
    }
  }

  /**
   * Returns a comparator function for sorting individuals by their 'affected' status.
   * @param individualsByGuid {object}
   * @returns {function(*, *): number}
   */
  static createIndividualSortComparator(individualsByGuid) {
    return (a, b) => ((individualsByGuid[b].affected === 'A' ? 1 : -1) - (individualsByGuid[a].affected === 'A' ? 1 : -1))
  }

  /**
   * Returns an object that maps each family filter drop-down option (CaseReviewTable.SHOW_*)
   * to the set of individual case review statuses (Individual.CASE_REVIEW_STATUS_*) that should
   * be shown when the user selects that particular filter.
   */
  static getFamilyToIndividualFilterMap() {
    return {
      [CaseReviewTable.SHOW_ACCEPTED]: [
        IndividualRow.CASE_REVIEW_STATUS_ACCEPTED_EXOME,
        IndividualRow.CASE_REVIEW_STATUS_ACCEPTED_GENOME,
        IndividualRow.CASE_REVIEW_STATUS_ACCEPTED_RNASEQ,
        IndividualRow.CASE_REVIEW_STATUS_ACCEPTED_PLATFORM_UNCERTAIN_KEY,
      ],
      [CaseReviewTable.SHOW_NOT_ACCEPTED]: [
        IndividualRow.CASE_REVIEW_STATUS_NOT_ACCEPTED_KEY,
      ],
      [CaseReviewTable.SHOW_IN_REVIEW]: [
        IndividualRow.CASE_REVIEW_STATUS_IN_REVIEW_KEY,
      ],
      [CaseReviewTable.SHOW_UNCERTAIN]: [
        IndividualRow.CASE_REVIEW_STATUS_UNCERTAIN_KEY,
        IndividualRow.CASE_REVIEW_STATUS_ACCEPTED_PLATFORM_UNCERTAIN_KEY,
      ],
      [CaseReviewTable.SHOW_MORE_INFO_NEEDED]: [
        IndividualRow.CASE_REVIEW_STATUS_MORE_INFO_NEEDED_KEY,
      ],
    }
  }

  /**
   * Returns a function which returns true if a given individual's caseReviewStatus is one of the
   * setOfStatusesToKeep.
   * @param individualsByGuid {object} maps each GUID to an object describing that individual.
   * @param setOfStatusesToKeep {Set} one or more Individual.CASE_REVIEW_STATUS_* constants.
   * @returns {function}
   */
  static createIndividualFilter(individualsByGuid, setOfStatusesToKeep) {
    /* Returns a function to filter individuals by caseReviewStatus */
    return (individualGuid) => {
      return setOfStatusesToKeep.has(individualsByGuid[individualGuid].caseReviewStatus)
    }
  }

  /**
   * Returns a function which returns true if a given family contains at least one individual that
   * passes the given familiesFilter.
   * @param familiesFilter {string} one of the CaseReviewTable.SHOW_* constants
   * @param familyGuidToIndivGuids {object}
   * @param individualsByGuid {object}
   * @returns {function}
   */
  static createFamilyFilter(familiesFilter, familyGuidToIndivGuids, individualsByGuid) {
    const individualsFilter = CaseReviewTable.createIndividualFilter(
      individualsByGuid,
      new Set(CaseReviewTable.getFamilyToIndividualFilterMap()[familiesFilter]),
    )

    //return true if at least 1 individual in the family has the matching caseReviewStatus
    return (familyGuid) => {
      if (familiesFilter === CaseReviewTable.SHOW_ALL) {
        return true
      }
      return familyGuidToIndivGuids[familyGuid].filter(individualsFilter).length > 0
    }
  }

  constructor(props) {
    super(props)

    const showDetails = localStorage.getItem(LOCAL_STORAGE_SHOW_DETAILS_KEY) || 'true'
    const familiesFilter = localStorage.getItem(LOCAL_STORAGE_FAMILIES_FILTER_KEY) || CaseReviewTable.SHOW_ALL
    const familiesSortOrder = localStorage.getItem(LOCAL_STORAGE_FAMILIES_SORT_ORDER_KEY) || CaseReviewTable.SORT_BY_FAMILY_NAME
    const familiesSortDirection = parseInt(localStorage.getItem(LOCAL_STORAGE_FAMILIES_SORT_DIRECTION_KEY) || '1', 10)

    this.state = {
      familiesFilter,
      familiesSortOrder,
      familiesSortDirection,
      showDetails: String(showDetails) === 'true',
    }
  }

  componentWillUpdate(nextProps, nextState) {
    // save current state if necessary
    if (this.state.showDetails !== nextState.showDetails) {
      localStorage.setItem(LOCAL_STORAGE_SHOW_DETAILS_KEY, nextState.showDetails)
    }
    if (this.state.familiesFilter !== nextState.familiesFilter) {
      localStorage.setItem(LOCAL_STORAGE_FAMILIES_FILTER_KEY, nextState.familiesFilter)
    }
    if (this.state.familiesSortOrder !== nextState.familiesSortOrder) {
      localStorage.setItem(LOCAL_STORAGE_FAMILIES_SORT_ORDER_KEY, nextState.familiesSortOrder)
    }
    if (this.state.familiesSortDirection !== nextState.familiesSortDirection) {
      localStorage.setItem(LOCAL_STORAGE_FAMILIES_SORT_DIRECTION_KEY, nextState.familiesSortDirection)
    }
  }

  render() {
    const {
      project,
      familiesByGuid,
      individualsByGuid,
      familyGuidToIndivGuids,
    } = this.props

    const CASE_REVIEW_STATUS_NAME_LOOKUP = IndividualRow.CASE_REVIEW_STATUS_OPTIONS.reduce(
      (acc, opt) => ({ ...acc, ...{ [opt.value]: opt.text } }), {},
    )

    const filteredFamilies = Object.keys(familiesByGuid)
      .filter(CaseReviewTable.createFamilyFilter(
        this.state.familiesFilter, familyGuidToIndivGuids, individualsByGuid))

    const caseReviewStatusCounts = Object.values(filteredFamilies).reduce((acc, familyGuid) => {
      familyGuidToIndivGuids[familyGuid].map((indivGuid) => {
        const k = CASE_REVIEW_STATUS_NAME_LOOKUP[individualsByGuid[indivGuid].caseReviewStatus]
        acc[k] = acc[k] ? acc[k] + 1 : 1
        return null
      })
      return acc
    }, {})

    return <Form>
      <div style={{ height: '5px' }} />
      <div style={{ float: 'right', padding: '0px 65px 10px 0px' }}>
        {filteredFamilies.length} families, &nbsp;
        {filteredFamilies.map(familyGuid => familyGuidToIndivGuids[familyGuid].length).reduce((a, b) => (a + b), 0)} individuals
      </div>
      <Table celled style={{ width: '100%' }}>

        <Table.Body>
          <Table.Row style={{ backgroundColor: '#F3F3F3' /*'#D0D3DD'*/ }}>
            <Table.Cell>
              <Grid stackable>
                <Grid.Column width={4}>
                  <FamiliesFilterSelector
                    filteredFamilies={filteredFamilies}
                    selectedFilter={this.state.familiesFilter}
                    onChange={this.handleFamiliesFilterChange}
                  />
                </Grid.Column>
                <Grid.Column width={4}>
                  <div style={{ whiteSpace: 'nowrap' }}>
                    <FamiliesSortOrderSelector
                      selectedSortOrder={this.state.familiesSortOrder}
                      onChange={this.handleFamiliesSortOrderChange}
                    />
                    <HorizontalSpacer width={5} />
                    <SortDirectionToggle
                      onClick={() => {
                        this.setState({
                          familiesSortDirection: -1 * this.state.familiesSortDirection,
                        })
                      }}
                      isPointingDown={this.state.familiesSortDirection === 1}
                    />
                  </div>
                </Grid.Column>
                <Grid.Column width={4}>
                  <b>Show Details:</b> &nbsp; &nbsp;
                  <HorizontalOnOffToggle
                    color="#4183c4"
                    isOn={this.state.showDetails}
                    onClick={this.handleDetailsToggle}
                  />
                </Grid.Column>
                <Grid.Column width={4}>
                  <span style={{ float: 'right', paddingRight: '50px' }}>
                    <b>Individual Statuses:</b><HorizontalSpacer width={10} />
                    <HorizontalStackedBar
                      width={100}
                      height={10}
                      title="Individual Statuses"
                      counts={caseReviewStatusCounts}
                      names={Object.values(IndividualRow.CASE_REVIEW_STATUS_OPTIONS).map(s => s.text)}
                      colors={[
                        '#2196F3',  //In Review
                        '#8BC34A',  //Uncertain
                        '#F44336',  //Accepted: Platform Uncertain
                        '#673AB7',  //Accepted: Exome
                        '#FFC107',  //Accepted: Genome
                        '#880E4F',  //Accepted: RNA-seq
                        '#C5CAE9',  //Not Accepted
                        'brown',    //Hold
                        'black',    //More Info Needed
                      ]}
                    />
                  </span>
                </Grid.Column>
              </Grid>
            </Table.Cell>
          </Table.Row>
          {
            (() => {
              if (filteredFamilies.length === 0) {
                return <Table.Row>
                  <Table.Cell style={{ padding: '10px 0px 10px 15px', color: 'gray', borderWidth: '0px' }}>
                    0 families {
                    this.state.familiesFilter !== CaseReviewTable.SHOW_ALL ?
                      'in this category' :
                      'under case review'
                  }
                  </Table.Cell>
                </Table.Row>
              }

              const sortedFamilies = filteredFamilies.sort(CaseReviewTable.createFamilySortComparator(
                  this.state.familiesSortOrder, this.state.familiesSortDirection, familiesByGuid, familyGuidToIndivGuids, individualsByGuid))
                .map((familyGuid, i) => {
                  const backgroundColor = (i % 2 === 0) ? 'white' : '#F3F3F3'
                  return <Table.Row key={familyGuid} style={{ backgroundColor }}>

                    <Table.Cell style={{ padding: '5px 0px 15px 15px' }}>
                      <FamilyRow
                        project={project}
                        family={familiesByGuid[familyGuid]}
                      />

                      <Table celled style={{
                        width: '100%',
                        margin: '0px',
                        backgroundColor: 'transparent',
                        borderWidth: '0px',
                      }}
                      >
                        <Table.Body>
                          {
                            familyGuidToIndivGuids[familyGuid].sort(
                              CaseReviewTable.createIndividualSortComparator(individualsByGuid),
                            ).map((individualGuid, j) => {
                              return <Table.Row key={j}>
                                <Table.Cell
                                  style={{ padding: '10px 0px 0px 15px', borderWidth: '0px' }}
                                >
                                  <IndividualRow
                                    project={project}
                                    family={familiesByGuid[familyGuid]}
                                    individual={individualsByGuid[individualGuid]}
                                    showDetails={this.state.showDetails}
                                  />
                                </Table.Cell>
                              </Table.Row>
                            })
                          }
                        </Table.Body>
                      </Table>
                    </Table.Cell>
                  </Table.Row>
                })

              return sortedFamilies
            })()
          }
          <Table.Row style={{ backgroundColor: '#F3F3F3' }} >
            <Table.Cell>
              <Grid stackable>
                <Grid.Column width={16} />
              </Grid>
            </Table.Cell>
          </Table.Row>
        </Table.Body>
      </Table>
    </Form>
  }

  handleFamiliesFilterChange = (event) => {
    this.setState({
      familiesFilter: event.target.value,
    })
  }

  handleFamiliesSortOrderChange = (event) => {
    this.setState({
      familiesSortOrder: event.target.value,
    })
  }

  handleDetailsToggle = () => {
    this.setState({ showDetails: !this.state.showDetails })
  }
}

export default CaseReviewTable


const FamiliesFilterSelector = props =>
  <div style={{ display: 'inline', whiteSpace: 'nowrap' }}>
    <span style={{ paddingLeft: '5px', paddingRight: '10px' }}><b>Show Families: </b></span>
    <select
      name="familiesFilter"
      value={props.selectedFilter}
      onChange={props.onChange}
      style={{ maxWidth: '137px', display: 'inline', padding: '0px !important' }}
    >
      <option value={CaseReviewTable.SHOW_ALL}>All</option>
      <option value={CaseReviewTable.SHOW_IN_REVIEW}>In Review</option>
      <option value={CaseReviewTable.SHOW_UNCERTAIN}>Uncertain</option>
      <option value={CaseReviewTable.SHOW_ACCEPTED}>Accepted</option>
      <option value={CaseReviewTable.SHOW_NOT_ACCEPTED}>Not Accepted</option>
      <option value={CaseReviewTable.SHOW_MORE_INFO_NEEDED}>More Info Needed</option>
    </select>
  </div>

FamiliesFilterSelector.propTypes = {
  selectedFilter: React.PropTypes.string.isRequired,
  onChange: React.PropTypes.func.isRequired,
}


const FamiliesSortOrderSelector = props =>
  <div style={{ display: 'inline' }}>
    <span style={{ paddingRight: '10px' }}><b>Sort By:</b></span>
    <select
      name="familiesSortOrder"
      value={props.selectedSortOrder}
      onChange={props.onChange}
      style={{ maxWidth: '130px', display: 'inline', padding: '0px !important' }}
    >
      <option value={CaseReviewTable.SORT_BY_FAMILY_NAME}>Family Name</option>
      <option value={CaseReviewTable.SORT_BY_DATE_ADDED}>Date Added</option>
      <option value={CaseReviewTable.SORT_BY_DATE_STATUS_CHANGED}>Last Changed</option>
    </select>
  </div>

FamiliesSortOrderSelector.propTypes = {
  selectedSortOrder: React.PropTypes.string.isRequired,
  onChange: React.PropTypes.func.isRequired,
}
