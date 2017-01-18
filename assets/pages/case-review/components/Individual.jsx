import React from 'react'
import { Grid, Icon, Form } from 'semantic-ui-react'

import PhenotipsDataView from './PhenotipsDataView'


class Individual extends React.Component
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
  static CASE_REVIEW_STATUS_ACCEPTED_EXOME_KEY = 'E'
  static CASE_REVIEW_STATUS_ACCEPTED_GENOME_KEY = 'G'
  static CASE_REVIEW_STATUS_NOT_ACCEPTED_KEY = 'R'
  static CASE_REVIEW_STATUS_MORE_INFO_NEEDED_KEY = 'Q'

  static CASE_REVIEW_STATUS_OPTIONS = [
    { value: '', text: '--' },
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

          <IndividualIdView family={family} individual={individual} />

        </Grid.Column>
        <Grid.Column width={10} style={{ padding: '0px' }}>

          <PhenotipsDataView
            projectId={project.projectId}
            individualId={individual.individualId}
            phenotipsId={individual.phenotipsId}
            phenotipsData={individual.phenotipsData}
            showDetails={showDetails}
          />

        </Grid.Column>
        <Grid.Column width={3}>

          <CaseReviewStatusSelector
            individualGuid={individual.individualGuid}
            defaultValue={individual.caseReviewStatus}
          />

        </Grid.Column>
      </Grid.Row>
    </Grid>
  }
}

const IndividualIdView = (props) => {
  const {
    individualId,
    paternalId,
    maternalId,
    sex,
    affected,
  } = props.individual

  return <span>
    <b>{
      <Icon style={{ fontSize: '13px' }} name={`
                ${(sex === 'U' || affected === 'U') ? 'help' : null}
                ${(sex === 'M' && affected === 'A') ? 'square' : null}
                ${(sex === 'F' && affected === 'A') ? 'circle' : null}
                ${(sex === 'M' && affected === 'N') ? 'square outline' : null}
                ${(sex === 'F' && affected === 'N') ? 'circle thin' : null}
              `}
      />
    }</b>

    &nbsp;{individualId}

    {
      (!props.family.pedigreeImage && ((paternalId && paternalId !== '.') || (maternalId && maternalId !== '.'))) ? (
        <div style={{ fontSize: '8pt' }}>
          child of &nbsp;
          <i>{(paternalId && maternalId) ? `${paternalId}, ${maternalId}` : (paternalId || maternalId) }</i>
        </div>
      ) : null
    }
  </span>
}

IndividualIdView.propTypes = {
  family: React.PropTypes.object.isRequired,
  individual: React.PropTypes.object.isRequired,
}


const CaseReviewStatusSelector = props =>
  <Form.Field
    tabIndex="1"
    defaultValue={props.defaultValue}
    control="select"
    name={`caseReviewStatus:${props.individualGuid}`}
    style={{ padding: '0px !important' }}
  >
    {
      Individual.CASE_REVIEW_STATUS_OPTIONS.map((option, k) =>
        <option key={k} value={`${option.value}`}>
          {option.text}
        </option>)
    }
  </Form.Field>

CaseReviewStatusSelector.propTypes = {
  individualGuid: React.PropTypes.string.isRequired,
  defaultValue: React.PropTypes.string.isRequired,
}


export default Individual

