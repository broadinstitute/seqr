import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import { Grid, Form } from 'semantic-ui-react'
import PedigreeIcon from './PedigreeIcon'
import PhenotipsDataView from './PhenotipsDataView'
import { formatDate } from '../../../shared/utils/dateUtils'
import SaveStatus from '../../../shared/components/form/SaveStatus'
import { HorizontalSpacer } from '../../../shared/components/Spacers'
import { HttpRequestHelper } from '../../../shared/utils/httpRequestHelper'
import { updateIndividualsByGuid } from '../reducers/rootReducer'


class IndividualRow extends React.Component
{
  static propTypes = {
    project: React.PropTypes.object.isRequired,
    family: React.PropTypes.object.isRequired,
    individual: React.PropTypes.object.isRequired,
    showDetails: React.PropTypes.bool.isRequired,
    updateIndividualsByGuid: React.PropTypes.func.isRequired,
  }

  static CASE_REVIEW_STATUS_IN_REVIEW_KEY = 'I'
  static CASE_REVIEW_STATUS_UNCERTAIN_KEY = 'U'
  static CASE_REVIEW_STATUS_ACCEPTED_PLATFORM_UNCERTAIN_KEY = 'A'
  static CASE_REVIEW_STATUS_ACCEPTED_EXOME = 'E'
  static CASE_REVIEW_STATUS_ACCEPTED_GENOME = 'G'
  static CASE_REVIEW_STATUS_ACCEPTED_RNASEQ = '3'
  static CASE_REVIEW_STATUS_NOT_ACCEPTED_KEY = 'R'
  static CASE_REVIEW_STATUS_MORE_INFO_NEEDED_KEY = 'Q'

  static CASE_REVIEW_STATUS_OPTIONS = [
    { value: 'I', text: 'In Review' },
    { value: 'U', text: 'Uncertain' },
    { value: 'A', text: 'Accepted: Platform Uncertain' },
    { value: 'E', text: 'Accepted: Exome' },
    { value: 'G', text: 'Accepted: Genome' },
    { value: '3', text: 'Accepted: RNA-seq' },
    { value: 'R', text: 'Not Accepted' },
    { value: 'H', text: 'Hold' },
    { value: 'Q', text: 'More Info Needed' },
  ]

  constructor(props) {
    super(props)

    this.state = { saveStatus: SaveStatus.NONE, saveErrorMessage: null }

    this.httpRequestHelper = new HttpRequestHelper(
      `/api/project/${props.project.projectGuid}/save_case_review_status`,
      this.handleSaveSuccess,
      this.handleSaveError,
      this.handleSaveClear,
    )
  }

  handleSaveSuccess = (responseJson) => {
    const individualsByGuid = responseJson
    this.props.updateIndividualsByGuid(individualsByGuid)
    if (this.mounted) {
      this.setState({ saveStatus: SaveStatus.SUCCEEDED })
    }
  }

  handleSaveError = (e) => {
    console.log('ERROR', e)
    if (this.mounted) {
      this.setState({ saveStatus: SaveStatus.ERROR, saveErrorMessage: e.message.toString() })
    }
  }

  handleSaveClear = () => {
    if (this.mounted) {
      this.setState({ saveStatus: SaveStatus.NONE, saveErrorMessage: null })
    }
  }

  componentWillMount() {
    this.mounted = true
  }

  componentWillUnmount() {
    this.mounted = false
  }

  render() {
    const {
      project,
      family,
      individual,
      showDetails,
    } = this.props

    return <Grid stackable style={{ width: '100%', padding: '15px 0px 15px 0px' }}>
      <Grid.Row style={{ padding: '0px' }}>
        <Grid.Column width={3} style={{ padding: '0px' }}>
          <IndividualLabelView family={family} individual={individual} showDetails={showDetails} />
        </Grid.Column>
        <Grid.Column width={10} style={{ padding: '0px' }}>
          <PhenotipsDataView
            project={project}
            individual={individual}
            showDetails={showDetails}
          />
        </Grid.Column>
        <Grid.Column width={3}>
          <div style={{ float: 'right', width: '200px' }}>
            <div className="nowrap">
              <CaseReviewStatusSelector
                individualGuid={individual.individualGuid}
                defaultValue={individual.caseReviewStatus}
                onSelect={(selectedValue) => {
                  this.httpRequestHelper.post({ form: { [individual.individualGuid]: selectedValue } })
                }}
              />
              <HorizontalSpacer width={5} />
              <SaveStatus status={this.state.saveStatus} errorMessage={this.state.saveErrorMessage} />
            </div>
            {
              showDetails ? (
                <div className="details-text" style={{ marginLeft: '2px' }}>
                  {formatDate('CHANGED', individual.caseReviewStatusLastModifiedDate)}
                  { individual.caseReviewStatusLastModifiedBy &&
                    ` BY ${individual.caseReviewStatusLastModifiedBy}`
                  }
                </div>
              ) : null
            }
          </div>
        </Grid.Column>
      </Grid.Row>
    </Grid>
  }
}

const IndividualLabelView = (props) => {
  const {
    individualId,
    displayName,
    paternalId,
    maternalId,
    sex,
    affected,
  } = props.individual

  return <span>
    <div style={{ display: 'inline-block', verticalAlign: 'top' }} >
      <b><PedigreeIcon style={{ fontSize: '13px' }} sex={sex} affected={affected} /></b>
    </div>
    <div style={{ display: 'inline-block' }} >
      &nbsp;{displayName || individualId}

      {
        (!props.family.pedigreeImage && ((paternalId && paternalId !== '.') || (maternalId && maternalId !== '.'))) ? (
          <div className="details-text">
            child of &nbsp;
            <i>{(paternalId && maternalId) ? `${paternalId}, ${maternalId}` : (paternalId || maternalId) }</i>
            <br />
          </div>
        ) : null
      }
      {
        props.showDetails ? (
          <div className="details-text">
            {formatDate('ADDED', props.individual.createdDate)}
          </div>
        ) : null
      }
    </div>
  </span>
}

IndividualLabelView.propTypes = {
  family: React.PropTypes.object.isRequired,
  individual: React.PropTypes.object.isRequired,
  showDetails: React.PropTypes.bool.isRequired,
}


const CaseReviewStatusSelector = (props) => {
  const onSelectHandler = props.onSelect
  return <div style={{ display: 'inline' }}>
    <Form.Field
      tabIndex="1"
      onChange={(e) => {
        const selectedValue = e.target.value
        onSelectHandler(selectedValue)
      }}
      defaultValue={props.defaultValue}
      control="select"
      name={`${props.individualGuid}`}
      style={{ margin: '3px !important', maxWidth: '170px', display: 'inline' }}
    >
      {
        IndividualRow.CASE_REVIEW_STATUS_OPTIONS.map((option, k) =>
          <option key={k} value={option.value}>{option.text}</option>)
      }
    </Form.Field>
  </div>
}


CaseReviewStatusSelector.propTypes = {
  onSelect: React.PropTypes.func.isRequired,
  individualGuid: React.PropTypes.string.isRequired,
  defaultValue: React.PropTypes.string.isRequired,
}


const mapDispatchToProps = dispatch => bindActionCreators({ updateIndividualsByGuid }, dispatch)

export default connect(null, mapDispatchToProps)(IndividualRow)
