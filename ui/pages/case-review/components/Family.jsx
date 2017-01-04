import React from 'react'
import { Grid, Icon } from 'semantic-ui-react'

import FamilyInfoView from './FamilyInfoView'
import Modal from '../../../shared/components/Modal'

class Family extends React.Component {

  static propTypes = {
    project: React.PropTypes.object.isRequired,
    family: React.PropTypes.object.isRequired,
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

    return <Grid stackable style={{ width: '100%' }}>
      <Grid.Row style={{ paddingTop: '20px', paddingRight: '10px' }}>
        <Grid.Column width={3}>
          <span style={{ paddingLeft: '0px' }}>
            <b>
              Family: &nbsp;
              <a href={`/project/${project.deprecatedProjectId}/family/${family.familyId}`}>
                {family.displayName}
              </a>
            </b>
            {
              (family.causalInheritanceMode && family.causalInheritanceMode !== 'unknown') ?
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
                  style={{ maxHeight: '100px', maxWidth: '150px', verticalAlign: 'top', cursor: 'zoom-in' }}
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
          <FamilyInfoView project={project} family={family} />
          <br />
        </Grid.Column>
      </Grid.Row>
    </Grid>
  }
}


export default Family


const PedigreeModal = props =>
  <Modal title={`Family ${props.family.displayName}`} onClose={props.onClose}>
    <center>
      <img src={props.family.pedigreeImage} alt="pedigree" style={{ maxHeight: '250px', maxWidth: '400px' }} /><br />
      <a href={props.family.pedigreeImage} target="_blank" rel="noopener noreferrer">
        <Icon name="zoom" /> Original Size
      </a>
    </center>
  </Modal>

PedigreeModal.propTypes = {
  family: React.PropTypes.object.isRequired,
  onClose: React.PropTypes.func.isRequired,
}

