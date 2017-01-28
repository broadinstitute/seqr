import React from 'react'
import { Grid } from 'semantic-ui-react'

import FamilyInfoView from './FamilyInfoView'
import Modal from '../../../shared/components/Modal'

class Family extends React.Component {

  static propTypes = {
    project: React.PropTypes.object.isRequired,
    family: React.PropTypes.object.isRequired,
    showDetails: React.PropTypes.bool,
  }

  constructor(props) {
    super(props)

    this.state = {
      showZoomedInPedigreeModal: false,
      showEditInternalSummaryModal: false,
      showEditInternalNoteModal: false,
    }
  }

  showZoomedInPedigreeModal = () => {
    this.setState({ showZoomedInPedigreeModal: true })
  }

  hideZoomedInPedigreeModal = () => {
    this.setState({ showZoomedInPedigreeModal: false })
  }

  render() {
    const {
      project,
      family,
    } = this.props

    return <Grid style={{ width: '100%' }}>
      <Grid.Row style={{ paddingTop: '20px', paddingRight: '10px' }}>
        <Grid.Column width={3}>
          <span style={{ paddingLeft: '0px' }}>
            <b>
              Family: &nbsp;
              <a href={`/project/${project.projectId}/family/${family.familyId}`}>
                {family.familyId}
              </a>
            </b>
            {(family.causalInheritanceMode && family.causalInheritanceMode !== 'unknown') ?
              `Inheritance: ${family.causalInheritanceMode}` :
              null
            }
            <br />
          </span>
          <br />
          {family.pedigreeImage ?
            <div>
              <a tabIndex="0" onClick={this.showZoomedInPedigreeModal}>
                <img src={family.pedigreeImage} alt="pedigree"
                  style={{ height: '80px', verticalAlign: 'top', cursor: 'zoom-in' }}
                />
              </a>
              {this.state.showZoomedInPedigreeModal ?
                <PedigreeModal family={family} onClose={this.hideZoomedInPedigreeModal} /> :
                null
              }
            </div> :
            null
          }
        </Grid.Column>

        <Grid.Column width={13}>
          <FamilyInfoView project={project} family={family} showDetails={this.props.showDetails} />
          <br />
        </Grid.Column>
      </Grid.Row>
    </Grid>
  }
}


export default Family


const PedigreeModal = props =>
  <Modal title={`Family ${props.family.familyId || props.family.familyName}`} onClose={props.onClose}>
    <img src={props.family.pedigreeImage} alt="pedigree" style={{ maxHeight: '250px', maxWidth: '400px' }} />
  </Modal>

PedigreeModal.propTypes = {
  family: React.PropTypes.object.isRequired,
  onClose: React.PropTypes.func.isRequired,
}

