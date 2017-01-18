/* eslint no-undef: "warn" */
import React from 'react'
import { Button, Form, Grid, Table } from 'semantic-ui-react'

import Family from './Family'
import Individual from './Individual'

import { HttpPost } from '../../../shared/js/httpUtils'
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
  static SHOW_IN_REVIEW = 'IN_REVIEW'
  static SHOW_UNCERTAIN = 'UNCERTAIN'
  static SHOW_ALL_ACCEPTED = 'ALL_ACCEPTED'
  static SHOW_NOT_ACCEPTED = 'NOT_ACCEPTED'
  static SHOW_MORE_INFO_NEEDED = 'MORE_INFO_NEEDED'

  constructor(props) {
    super(props)

    const showDetails = localStorage.getItem(LOCAL_STORAGE_SHOW_DETAILS_KEY)
    const familiesFilter = localStorage.getItem(LOCAL_STORAGE_FAMILIES_FILTER_KEY)

    this.state = {
      saveStatus: SaveStatus.NONE,
      saveErrorMessage: null,
      familiesFilter: familiesFilter || CaseReviewTable.SHOW_ALL,
      showDetails: showDetails !== undefined ? String(showDetails) === 'true' : true,
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
        console.log(e)
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
                    familiesFilter={this.state.familiesFilter}
                    onChange={this.handleFamiliesFilterChange}
                  />
                </Grid.Column>
                <Grid.Column width={8}>

                  <b>Phenotype Details:</b> &nbsp; &nbsp;
                  <Toggle
                    color="#4183c4"
                    isOn={this.state.showDetails}
                    onClick={() => this.setState({ showDetails: !this.state.showDetails })}
                  />
                </Grid.Column>
                <Grid.Column width={3}>
                  <div style={{ float: 'right' }}>
                    <SaveButton />
                    <SaveStatus status={this.state.saveStatus} errorMessage={this.state.saveErrorMessage} />
                  </div>
                </Grid.Column>
              </Grid>
            </Table.Cell>
          </Table.Row>
          {

            Object.keys(familiesByGuid)
              .filter((familyGuid) => {
                //this.state.familiesFilter = CaseReviewTable.SHOW_UNCERTAIN
                const createFilterFunc = setOfStatusesToKeep => (individualGuid) => {
                  const caseReviewStatus = individualsByGuid[individualGuid].caseReviewStatus
                  return setOfStatusesToKeep.has(caseReviewStatus)
                }
                switch (this.state.familiesFilter) {
                  case CaseReviewTable.SHOW_ALL:
                    return true
                  case CaseReviewTable.SHOW_IN_REVIEW:
                    return familyGuidToIndivGuids[familyGuid].filter(
                        createFilterFunc(new Set([Individual.CASE_REVIEW_STATUS_IN_REVIEW_KEY]))).length > 0
                  case CaseReviewTable.SHOW_UNCERTAIN:
                    return familyGuidToIndivGuids[familyGuid].filter(
                      createFilterFunc(new Set([Individual.CASE_REVIEW_STATUS_UNCERTAIN_KEY, Individual.CASE_REVIEW_STATUS_ACCEPTED_PLATFORM_UNCERTAIN_KEY]))).length > 0
                  case CaseReviewTable.SHOW_ALL_ACCEPTED:
                    return familyGuidToIndivGuids[familyGuid].filter(
                        createFilterFunc(new Set([Individual.CASE_REVIEW_STATUS_ACCEPTED_EXOME_KEY, Individual.CASE_REVIEW_STATUS_ACCEPTED_GENOME_KEY, Individual.CASE_REVIEW_STATUS_ACCEPTED_PLATFORM_UNCERTAIN_KEY]))).length === familyGuidToIndivGuids[familyGuid].length
                  case CaseReviewTable.SHOW_NOT_ACCEPTED:
                    return familyGuidToIndivGuids[familyGuid].filter(
                        createFilterFunc(new Set([Individual.CASE_REVIEW_STATUS_NOT_ACCEPTED_KEY]))).length === familyGuidToIndivGuids[familyGuid].length
                  case CaseReviewTable.SHOW_MORE_INFO_NEEDED:
                    return familyGuidToIndivGuids[familyGuid].filter(
                      createFilterFunc(new Set([Individual.CASE_REVIEW_STATUS_MORE_INFO_NEEDED_KEY]))).length > 0
                  default:
                    console.error(`Unexpected familiesFilter value: '${this.state.familiesFilter}'`)
                    return true
                }
              })
              .map((familyGuid, i) => {
                const backgroundColor = (i % 2 === 0) ? 'white' : '#F3F3F3'
                return <Table.Row key={familyGuid} style={{ backgroundColor }}>

                  <Table.Cell style={{ padding: '5px 0px 15px 15px' }}>
                    <Family
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
                          familyGuidToIndivGuids[familyGuid].map((individualGuid, j) => {
                            return <Table.Row key={j}>
                              <Table.Cell style={{ padding: '10px 0px 0px 15px', borderWidth: '0px' }}>
                                <Individual
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

    const jsonObj = Object.keys(serializedFormData).reduce((result, key) => {
      if (key.startsWith('caseReviewStatus')) {
        const individualId = key.split(':')[1]
        result[individualId] = serializedFormData[key]
      }
      return result
    }, {})

    this.httpPostSubmitter.submit({ form: jsonObj })
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
      value={props.familiesFilter}
      onChange={props.onChange}
      style={{ width: '100px', display: 'inline', padding: '0px !important' }}
    >
      <option value={CaseReviewTable.SHOW_ALL}>All</option>
      <option value={CaseReviewTable.SHOW_IN_REVIEW}>In Review</option>
      <option value={CaseReviewTable.SHOW_UNCERTAIN}>Uncertain</option>
      <option value={CaseReviewTable.SHOW_ALL_ACCEPTED}>All Accepted</option>
      <option value={CaseReviewTable.SHOW_NOT_ACCEPTED}>Not Accepted</option>
      <option value={CaseReviewTable.SHOW_MORE_INFO_NEEDED}>More Info Needed</option>
    </select>
  </div>

FamiliesFilterSelector.propTypes = {
  familiesFilter: React.PropTypes.string.isRequired,
  onChange: React.PropTypes.func.isRequired,
}


const SaveButton = () =>
  <Button
    basic
    type="submit"
    style={{
      padding: '5px',
      width: '100px',
      backgroundColor: 'white !important',
    }}
  >
    <span style={{ color: 'black' }}>Save</span>
  </Button>

/*
 <Button basic type="submit" style={{
 padding: '5px',
 width: '100px',
 marginRight: '27px',
 float: 'right' }}
 >
 <span style={{ marginLeft: '22px', color: 'black' }}>Save</span>
 <span style={{ float: 'right' }}>
 <SaveStatus status={this.state.saveStatus} errorMessage={this.state.saveErrorMessage} />
 </span>
 </Button>
*/
