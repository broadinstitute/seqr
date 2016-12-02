/* eslint no-undef: "warn" */
import React from 'react'
import injectSheet from 'react-jss'
import { Button, Form, Table, Icon } from 'semantic-ui-react'

import Family from './Family'
import Individual from './Individual'
import SaveStatus from './SaveStatus'
import HttpPost from './HttpUtils'

import { HorizontalSpacer } from '../../../shared/components/Spacers'

const LOCAL_STORAGE_SHOW_DETAILS_KEY = 'CaseReviewTable.showDetails'
const LOCAL_STORAGE_FAMILIES_FILTER_KEY = 'CaseReviewTable.familiesFilter'


const styles = {
  div: {
    backgroundColor: 'pink',
    color: 'red',
    border: '2px solid black',
    padding: '0px !important',
  },
}

@injectSheet(styles)
class CaseReviewTable extends React.Component {

  static propTypes = {
    project: React.PropTypes.object.isRequired,
    familiesByGuid: React.PropTypes.object.isRequired,
    individualsByGuid: React.PropTypes.object.isRequired,
    familyGuidToIndivGuids: React.PropTypes.object.isRequired,
  }

  static SHOW_ALL = 'ALL'
  static SHOW_IN_REVIEW = 'IN_REVIEW'
  static SHOW_UNCERTAIN = 'UNCERTAIN'
  static SHOW_MORE_INFO_NEEDED = 'MORE_INFO_NEEDED'

  constructor(props) {
    super(props)

    const showDetails = localStorage.getItem(LOCAL_STORAGE_SHOW_DETAILS_KEY)
    const familiesFilter = localStorage.getItem(LOCAL_STORAGE_FAMILIES_FILTER_KEY)

    const individualGuidToCaseReviewStatus = Object.keys(this.props.individualsByGuid).reduce((result, individualId) => {
      result[individualId] = this.props.individualsByGuid[individualId].caseReviewStatus
      return result
    }, {})

    this.state = {
      saveStatus: SaveStatus.NONE,
      saveErrorMessage: null,
      familiesFilter: familiesFilter || CaseReviewTable.SHOW_ALL,
      showDetails: showDetails !== undefined ? String(showDetails) === 'true' : true,
      individualGuidToCaseReviewStatus,
    }

    this.httpPostSubmitter = new HttpPost(
      `/api/project/${this.props.project.projectGuid}/save_case_review_status`,
      (response, savedJson) => {
        this.setState({
          saveStatus: SaveStatus.SUCCEEDED,
          individualGuidToCaseReviewStatus: {
            ...this.state.individualGuidToCaseReviewStatus,
            ...savedJson.form,
          },
        })
      },
      e => this.setState({ saveStatus: SaveStatus.ERROR, saveErrorMessage: e.message.toString() }),
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
              <FamiliesFilterSelector
                familiesFilter={this.state.familiesFilter}
                onChange={this.handleFamiliesFilterChange}
              />

              <HorizontalSpacer width={35} />
              <b>Phenotype Details:</b> &nbsp; &nbsp;
              <Toggle
                color="#4183c4"
                isOn={this.state.showDetails}
                onClick={() => this.setState({ showDetails: !this.state.showDetails })}
              />
              <div style={{ float: 'right' }}>
                <SaveButton />
                <SaveStatus status={this.state.saveStatus} errorMessage={this.state.saveErrorMessage} />
              </div>
            </Table.Cell>
          </Table.Row>
          {
            Object.keys(familiesByGuid)
              .filter((familyGuid) => {
                switch (this.state.familiesFilter) {
                  case CaseReviewTable.SHOW_ALL:
                    return true
                  case CaseReviewTable.SHOW_IN_REVIEW:
                    return familyGuidToIndivGuids[familyGuid].filter((individualGuid) => {
                      const caseReviewStatus = this.state.individualGuidToCaseReviewStatus[individualGuid]
                      return caseReviewStatus === Individual.CASE_REVIEW_STATUS_IN_REVIEW_KEY
                    }).length > 0
                  case CaseReviewTable.SHOW_UNCERTAIN:
                    return familyGuidToIndivGuids[familyGuid].filter((individualGuid) => {
                      const caseReviewStatus = this.state.individualGuidToCaseReviewStatus[individualGuid]
                      return caseReviewStatus === Individual.CASE_REVIEW_STATUS_UNCERTAIN_KEY ||
                              caseReviewStatus === Individual.CASE_REVIEW_STATUS_ACCEPTED_PLATFORM_UNCERTAIN_KEY
                    }).length > 0
                  case CaseReviewTable.SHOW_MORE_INFO_NEEDED:
                    return familyGuidToIndivGuids[familyGuid].filter((individualGuid) => {
                      const caseReviewStatus = this.state.individualGuidToCaseReviewStatus[individualGuid]
                      return caseReviewStatus === Individual.CASE_REVIEW_STATUS_MORE_INFO_NEEDED_KEY
                    }).length > 0
                  default:
                    throw new Error(`Unexpected familiesFilter value: ${this.state.familiesFilter}`)
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
                                  individual={{
                                    ...individualsByGuid[individualGuid],
                                    caseReviewStatus: this.state.individualGuidToCaseReviewStatus[individualGuid],
                                  }}
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
              <div style={{ float: 'right' }}>
                <SaveButton />
                <SaveStatus status={this.state.saveStatus} errorMessage={this.state.saveErrorMessage} />
              </div>
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
      <option value={CaseReviewTable.SHOW_MORE_INFO_NEEDED}>More Info Needed</option>
    </select>
  </div>

FamiliesFilterSelector.propTypes = {
  familiesFilter: React.PropTypes.string.isRequired,
  onChange: React.PropTypes.func.isRequired,
}


const Toggle = props =>
  <a
    tabIndex="0"
    onClick={props.onClick}
    ref={(ref) => { if (ref) ref.blur() }}
    style={{  /* prevent text selection on click */
      WebkitUserSelect: 'none', /* webkit (safari, chrome) browsers */
      MozUserSelect: 'none', /* mozilla browsers */
      KhtmlUserSelect: 'none', /* webkit (konqueror) browsers */
      MsUserSelect: 'none', /* IE10+ */
      verticalAlign: 'bottom',
    }}
  >
    {props.isOn ?
      <Icon size="large" style={{ cursor: 'pointer', color: props.color || '#BBBBBB' }} name="toggle on" /> :
      <Icon size="large" style={{ cursor: 'pointer', color: '#BBBBBB' }} name="toggle off" />
    }
  </a>

Toggle.propTypes = {
  onClick: React.PropTypes.func.isRequired,
  isOn: React.PropTypes.bool.isRequired,
  color: React.PropTypes.string,
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
