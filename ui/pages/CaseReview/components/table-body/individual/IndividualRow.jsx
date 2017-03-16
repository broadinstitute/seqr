import React from 'react'
import { connect } from 'react-redux'

import { Grid } from 'semantic-ui-react'

import CaseReviewStatusDropdown from './CaseReviewStatusDropdown'
import PhenotipsDataView from './PhenotipsDataView'
import { getProject, getShowDetails } from '../../../reducers/rootReducer'
import { formatDate } from '../../../../../shared/utils/dateUtils'
import PedigreeIcon from '../../../../../shared/components/icons/PedigreeIcon'

const detailsStyle = {
  padding: '5px 0 5px 5px',
  fontSize: '11px',
  fontWeight: '500',
  color: '#999999',
}

class IndividualRow extends React.Component
{
  static propTypes = {
    project: React.PropTypes.object.isRequired,
    family: React.PropTypes.object.isRequired,
    individual: React.PropTypes.object.isRequired,
    showDetails: React.PropTypes.bool.isRequired,
  }

  render() {
    const { project, family, individual, showDetails } = this.props

    const { individualId, displayName, paternalId, maternalId, sex, affected, createdDate } = individual

    return <Grid stackable style={{ width: '100%' }}>
      <Grid.Row style={{ padding: '0px' }}>
        <Grid.Column width={3} style={{ padding: '0px 0px 15px 15px' }}>
          <span>
            <div style={{ display: 'inline-block', verticalAlign: 'top' }} >
              <PedigreeIcon style={{ fontSize: '13px' }} sex={sex} affected={affected} />
            </div>
            <div style={{ display: 'inline-block' }} >
              &nbsp;
              {displayName || individualId}
              {
                (!family.pedigreeImage && ((paternalId && paternalId !== '.') || (maternalId && maternalId !== '.'))) ? (
                  <div style={detailsStyle}>
                    child of &nbsp;
                    <i>{(paternalId && maternalId) ? `${paternalId}, ${maternalId}` : (paternalId || maternalId) }</i>
                    <br />
                  </div>
                ) : null
              }
              {
                showDetails ? (
                  <div style={detailsStyle}>
                    {formatDate('ADDED', createdDate)}
                  </div>
                  ) : null
              }
            </div>
          </span>
        </Grid.Column>
        <Grid.Column width={10}>
          <PhenotipsDataView project={project} individual={individual} showDetails={showDetails} />
        </Grid.Column>
        <Grid.Column width={3}>
          <div style={{ float: 'right', width: '200px' }}>
            <CaseReviewStatusDropdown individual={individual} />
            {
              showDetails ? (
                <div style={{ ...detailsStyle, marginLeft: '2px' }}>
                  {formatDate('CHANGED', individual.caseReviewStatusLastModifiedDate)}
                  { individual.caseReviewStatusLastModifiedBy && ` BY ${individual.caseReviewStatusLastModifiedBy}` }
                </div>
              ) : null
            }
          </div>
        </Grid.Column>
      </Grid.Row>
    </Grid>
  }
}

export { IndividualRow as IndividualRowComponent }

const mapStateToProps = state => ({
  project: getProject(state),
  showDetails: getShowDetails(state),
})

export default connect(mapStateToProps)(IndividualRow)
