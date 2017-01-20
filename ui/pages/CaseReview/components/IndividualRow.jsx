import React from 'react'
import { Grid, Form } from 'semantic-ui-react'
import PedigreeIcon from './PedigreeIcon'
import PhenotipsDataView from './PhenotipsDataView'
import { formatDate } from '../../../shared/utils/dateUtils'

class IndividualRow extends React.Component
{
  static propTypes = {
    project: React.PropTypes.object.isRequired,
    family: React.PropTypes.object.isRequired,
    individual: React.PropTypes.object.isRequired,
    showDetails: React.PropTypes.bool.isRequired,
  }

  static CASE_REVIEW_STATUS_IN_REVIEW_KEY = 'I'
  static CASE_REVIEW_STATUS_UNCERTAIN_KEY = 'U'
  static CASE_REVIEW_STATUS_ACCEPTED_PLATFORM_UNCERTAIN_KEY = 'A'
  static CASE_REVIEW_STATUS_ACCEPTED_EXOME = 'E'
  static CASE_REVIEW_STATUS_ACCEPTED_GENOME = 'G'
  static CASE_REVIEW_STATUS_NOT_ACCEPTED_KEY = 'R'
  static CASE_REVIEW_STATUS_MORE_INFO_NEEDED_KEY = 'Q'

  static CASE_REVIEW_STATUS_OPTIONS = [
    { value: 'I', text: 'In Review' },
    { value: 'U', text: 'Uncertain' },
    { value: 'A', text: 'Accepted: Platform Uncertain' },
    { value: 'E', text: 'Accepted: Exome' },
    { value: 'G', text: 'Accepted: Genome' },
    { value: 'R', text: 'Not Accepted' },
    { value: 'H', text: 'Hold' },
    { value: 'Q', text: 'More Info Needed' },
  ]

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
          <CaseReviewStatusSelector
            individualGuid={individual.individualGuid}
            defaultValue={individual.caseReviewStatus}
          />
          {
            showDetails ? (
              <div className="details-text" style={{ textAlign: 'center' }}>
                {formatDate('SET', individual.caseReviewStatusLastModifiedDate)}
                { individual.caseReviewStatusLastModifiedBy ? ` BY ${individual.caseReviewStatusLastModifiedBy}` : null }
              </div>
            ) : null
          }
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


const CaseReviewStatusSelector = props =>
  <Form.Field
    tabIndex="1"
    defaultValue={props.defaultValue}
    control="select"
    name={`caseReviewStatus:${props.individualGuid}`}
    style={{ margin: '3px !important' }}
  >
    {
      IndividualRow.CASE_REVIEW_STATUS_OPTIONS.map((option, k) =>
        <option key={k} value={option.value}>
          {option.text}
        </option>)
    }
  </Form.Field>

CaseReviewStatusSelector.propTypes = {
  individualGuid: React.PropTypes.string.isRequired,
  defaultValue: React.PropTypes.string.isRequired,
}


export default IndividualRow

