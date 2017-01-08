/* eslint no-undef: "warn" */
import React from 'react'
import { Button, Form, Grid, Table } from 'semantic-ui-react'

import FamilyRow from './FamilyRow'
import IndividualRow from './IndividualRow'

import { HttpPost } from '../../../shared/utils/httpPostHelper'
import Toggle from '../../../shared/components/form/Toggle'
import SaveStatus from '../../../shared/components/form/SaveStatus'

const LOCAL_STORAGE_SHOW_DETAILS_KEY = 'CaseReviewTable.showDetails'
const LOCAL_STORAGE_FAMILIES_FILTER_KEY = 'CaseReviewTable.familiesFilter'


class CaseReviewTable extends React.Component {

  static propTypes = {
    project: React.PropTypes.object.isRequired,
    familiesByGuid: React.PropTypes.object.isRequired,
    individualsByGuid: React.PropTypes.object.isRequired,
    familyGuidToIndivGuids: React.PropTypes.object.isRequired,
    updateCaseReviewStatuses: React.PropTypes.func.isRequired,
  }

  static SHOW_ALL = 'ALL'
  static SHOW_ACCEPTED = 'ACCEPTED'
  static SHOW_IN_REVIEW = 'IN_REVIEW'
  static SHOW_UNCERTAIN = 'UNCERTAIN'
  static SHOW_MORE_INFO_NEEDED = 'MORE_INFO_NEEDED'

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

    this.state = {
      familiesFilter: familiesFilter || CaseReviewTable.SHOW_ALL,
      showDetails: String(showDetails) === 'true',
      saveStatus: SaveStatus.NONE,
      saveErrorMessage: null,
    }

    this.httpPostSubmitter = new HttpPost(
      `/api/project/${this.props.project.projectGuid}/save_case_review_status`,
      (response, savedJson) => {
        this.setState({
          saveStatus: SaveStatus.SUCCEEDED,
        })
        const individualGuidToCaseReviewStatus = savedJson.form
        this.props.updateCaseReviewStatuses(individualGuidToCaseReviewStatus)
      },
      (e) => {
        console.log('ERROR', e)
        this.setState({ saveStatus: SaveStatus.ERROR, saveErrorMessage: e.message.toString() })
      },
      () => this.setState({ saveStatus: SaveStatus.NONE, saveErrorMessage: null }),
    )
  }

  render() {
    const {
      project,
      familiesByGuid,
      individualsByGuid,
      familyGuidToIndivGuids,
    } = this.props

    // save current state
    localStorage.setItem(LOCAL_STORAGE_SHOW_DETAILS_KEY, this.state.showDetails)
    localStorage.setItem(LOCAL_STORAGE_FAMILIES_FILTER_KEY, this.state.familiesFilter)

    return <Form onSubmit={this.handleSave}>
      <div style={{ height: '5px' }} />
      <Table celled style={{ width: '100%' }}>

        <Table.Body>
          <Table.Row style={{ backgroundColor: '#F3F3F3' /*'#D0D3DD'*/ }}>
            <Table.Cell>
              <Grid stackable>
                <Grid.Column width={5}>
                  <FamiliesFilterSelector
                    selectedFilter={this.state.familiesFilter}
                    onChange={this.handleFamiliesFilterChange}
                  />
                </Grid.Column>
                <Grid.Column width={8}>
                  <b>Phenotype Details:</b> &nbsp; &nbsp;
                  <Toggle
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
                            (a, b) => {
                              return (individualsByGuid[b].affected === 'A' ? 1 : -1) - (individualsByGuid[a].affected === 'A' ? 1 : -1)
                            },
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
      style={{ width: '100px', display: 'inline', padding: '0px !important' }}
    >
      <option value={CaseReviewTable.SHOW_ALL}>All</option>
      <option value={CaseReviewTable.SHOW_ACCEPTED}>Accepted</option>
      <option value={CaseReviewTable.SHOW_IN_REVIEW}>In Review</option>
      <option value={CaseReviewTable.SHOW_UNCERTAIN}>Uncertain</option>
      <option value={CaseReviewTable.SHOW_MORE_INFO_NEEDED}>More Info Needed</option>
    </select>
  </div>

FamiliesFilterSelector.propTypes = {
  selectedFilter: React.PropTypes.string.isRequired,
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

