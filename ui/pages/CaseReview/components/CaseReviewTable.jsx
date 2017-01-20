import React from 'react'
import { Button, Form, Grid, Table } from 'semantic-ui-react'
import max from 'lodash/max'
import FamilyRow from './FamilyRow'
import IndividualRow from './IndividualRow'

import { HttpPost } from '../../../shared/utils/httpPostHelper'
import { SortDirectionToggle, HorizontalOnOffToggle } from '../../../shared/components/form/Toggle'
import SaveStatus from '../../../shared/components/form/SaveStatus'
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
    updateIndividualsByGuid: React.PropTypes.func.isRequired,
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
        console.error(`Unexpected familiesSortOrder value: ${familiesSortOrder}`)
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
      saveStatus: SaveStatus.NONE,
      saveErrorMessage: null,
    }

    this.httpPostSubmitter = new HttpPost(
      `/api/project/${this.props.project.projectGuid}/save_case_review_status`,
      (responseJson) => {
        this.setState({
          saveStatus: SaveStatus.SUCCEEDED,
        })
        const individualsByGuid = responseJson
        this.props.updateIndividualsByGuid(individualsByGuid)
      },
      (e) => {
        console.log('ERROR', e)
        this.setState({ saveStatus: SaveStatus.ERROR, saveErrorMessage: e.message.toString() })
      },
      () => this.setState({ saveStatus: SaveStatus.NONE, saveErrorMessage: null }),
    )
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

    return <Form onSubmit={this.handleSave}>
      <div style={{ height: '5px' }} />
      <Table celled style={{ width: '100%' }}>

        <Table.Body>
          <Table.Row style={{ backgroundColor: '#F3F3F3' /*'#D0D3DD'*/ }}>
            <Table.Cell>
              <Grid stackable>
                <Grid.Column width={4}>
                  <FamiliesFilterSelector
                    selectedFilter={this.state.familiesFilter}
                    onChange={this.handleFamiliesFilterChange}
                  />
                </Grid.Column>
                <Grid.Column width={5}>
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
                </Grid.Column>
                <Grid.Column width={4}>
                  <b>Show Details:</b> &nbsp; &nbsp;
                  <HorizontalOnOffToggle
                    color="#4183c4"
                    isOn={this.state.showDetails}
                    onClick={this.handleDetailsToggle}
                  />
                </Grid.Column>
                <Grid.Column width={3}>
                  <div style={{ float: 'right' }}>
                    <SaveButton />
                    <SaveStatus
                      status={this.state.saveStatus}
                      errorMessage={this.state.saveErrorMessage}
                    />
                  </div>
                </Grid.Column>
              </Grid>
            </Table.Cell>
          </Table.Row>
          {

            Object.keys(familiesByGuid)
              .filter(CaseReviewTable.createFamilyFilter(
                this.state.familiesFilter, familyGuidToIndivGuids, individualsByGuid))
              .sort(CaseReviewTable.createFamilySortComparator(
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
                      borderWidth: '0px' }}
                    >
                      <Table.Body>
                        {
                          familyGuidToIndivGuids[familyGuid].sort(
                            CaseReviewTable.createIndividualSortComparator(individualsByGuid),
                          ).map((individualGuid, j) => {
                            return <Table.Row key={j}>
                              <Table.Cell style={{ padding: '10px 0px 0px 15px', borderWidth: '0px' }}>
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
          }
          <Table.Row style={{ backgroundColor: '#F3F3F3' }} >
            <Table.Cell>
              <Grid stackable>
                <Grid.Column width={16}>
                  <div style={{ float: 'right' }}>
                    <SaveButton />
                    <SaveStatus status={this.state.saveStatus} errorMessage={this.state.saveErrorMessage} />
                  </div>
                </Grid.Column>
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

  handleSave = (event, serializedFormData) => {
    event.preventDefault()

    this.setState({
      saveStatus: SaveStatus.IN_PROGRESS,
      saveErrorMessage: null,
    })

    const jsonObj = Object.keys(serializedFormData.formData).reduce((result, key) => {
      if (key.startsWith('caseReviewStatus')) {
        const individualId = key.split(':')[1]
        result[individualId] = serializedFormData.formData[key]
      }
      return result
    }, {})

    this.httpPostSubmitter.submit({ form: jsonObj })
  }

  handleDetailsToggle = () => {
    this.setState({ showDetails: !this.state.showDetails })
  }
}

export default CaseReviewTable


const FamiliesFilterSelector = props =>
  <div style={{ display: 'inline' }}>
    <span style={{ paddingLeft: '5px', paddingRight: '10px' }}>
      <b>Show Families:</b>
    </span>
    <select
      name="familiesFilter"
      value={props.selectedFilter}
      onChange={props.onChange}
      style={{ width: '137px', display: 'inline', padding: '0px !important' }}
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
      style={{ width: '130px', display: 'inline', padding: '0px !important' }}
    >
      <option value={CaseReviewTable.SORT_BY_FAMILY_NAME}>Family Name</option>
      <option value={CaseReviewTable.SORT_BY_DATE_ADDED}>Date Added</option>
      <option value={CaseReviewTable.SORT_BY_DATE_STATUS_CHANGED}>Date Status Changed</option>
    </select>
  </div>

FamiliesSortOrderSelector.propTypes = {
  selectedSortOrder: React.PropTypes.string.isRequired,
  onChange: React.PropTypes.func.isRequired,
}


const SaveButton = () =>
  <Button
    id="save-button"
    basic
    type="submit"
    style={{
      padding: '5px',
      width: '100px',
    }}
  >
    <span style={{ color: 'black' }}>Save</span>
  </Button>

