import React from 'react'
import { Grid, Icon, Form } from 'semantic-ui-react'

import { HorizontalSpacer } from '../../../shared/components/Spacers'

import PhenotipsDataView from './PhenotipsDataView'
import PhenotipsPDFModal from './PhenotipsPDFModal'


class Individual extends React.Component
{
  static propTypes = {
    project: React.PropTypes.object.isRequired,
    family: React.PropTypes.object.isRequired,
    individual: React.PropTypes.object.isRequired,
  }

  static CASE_REVIEW_STATUS_IN_REVIEW_KEY = 'I'
  static CASE_REVIEW_STATUS_UNCERTAIN_KEY = 'U'

  static CASE_REVIEW_STATUS_OPTIONS = [
    { value: '', text: '    --     ' },
    { value: 'I', text: 'In Review' },
    { value: 'U', text: 'Uncertain' },
    { value: 'A', text: 'Accepted' },
    { value: 'E', text: 'Accepted: Exome' },
    { value: 'G', text: 'Accepted: Genome' },
    { value: 'R', text: 'Not Accepted' },
    { value: 'N', text: 'See Notes' },
    { value: 'H', text: 'Hold' },
  ]

  constructor(props) {
    super(props)

    this.state = {
      showPhenotipsPDFModal: false,
    }
  }

  showPhenotipsPDFModal = () =>
    this.setState({ showPhenotipsPDFModal: true })

  hidePhenotipsPDFModal = () =>
    this.setState({ showPhenotipsPDFModal: false })


  render() {
    const {
      project,
      family,
      individual,
    } = this.props

    return <Grid stackable style={{ width: '100%', padding: '15px 0px 15px 0px' }}>
      <Grid.Row style={{ padding: '0px' }}>
        <Grid.Column width={3} style={{ padding: '0px' }}>

          <IndividualIdView family={family} individual={individual} />

          <HorizontalSpacer width={25} />

          <div style={{ display: 'inline-block', float: 'right', paddingRight: '20px' }}>
            <a tabIndex="0" onClick={this.showPhenotipsPDFModal} style={{ cursor: 'pointer' }}>
              <Icon name="file pdf outline" title="PhenoTips PDF" />
            </a>
            {this.state.showPhenotipsPDFModal ?
              <PhenotipsPDFModal
                projectId={project.projectId}
                phenotipsId={individual.phenotipsId}
                individualId={individual.individualId}
                hidePhenotipsPDFModal={this.hidePhenotipsPDFModal}
              /> :
              null
            }
          </div>

        </Grid.Column>
        <Grid.Column width={10} style={{ padding: '0px' }}>

          {individual.phenotipsData ?
            <PhenotipsDataView phenotipsData={individual.phenotipsData} /> :
            null
          }

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
      (!props.family.pedigreeImage && (paternalId || maternalId)) ? (
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
  >
    {
      Individual.CASE_REVIEW_STATUS_OPTIONS.map((option, k) =>
        <option key={k} value={option.value}>
          {option.text}
        </option>)
    }
  </Form.Field>

CaseReviewStatusSelector.propTypes = {
  individualGuid: React.PropTypes.string.isRequired,
  defaultValue: React.PropTypes.string.isRequired,
}


export default Individual

