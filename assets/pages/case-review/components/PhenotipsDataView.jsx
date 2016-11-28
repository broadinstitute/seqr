/* eslint no-unused-expressions: 0 */

import React from 'react'
import injectSheet from 'react-jss'
import { Icon } from 'semantic-ui-react'

import { HorizontalSpacer } from '../../../shared/components/Spacers'
import PhenotipsPDFModal from './PhenotipsPDFModal'


const styles = {
  infoDiv: {
    paddingLeft: '20px',
  },
}


@injectSheet(styles)
class PhenotipsDataView extends React.Component
{

  static propTypes = {
    projectId: React.PropTypes.string.isRequired,
    individualId: React.PropTypes.string.isRequired,
    phenotipsId: React.PropTypes.string.isRequired,
    phenotipsData: React.PropTypes.object,
    sheet: React.PropTypes.object,
  }

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
    const { projectId, individualId, phenotipsId, phenotipsData } = this.props
    const classNames = this.props.sheet.classes

    return <div>
      <b>PhenoTips:</b>

      <HorizontalSpacer width={15} />

      <div style={{ display: 'inline-block' }}>
        <a tabIndex="0" onClick={this.showPhenotipsPDFModal} style={{ cursor: 'pointer' }}>
          <Icon name="file pdf outline" title="PhenoTips PDF" />
        </a>
        {this.state.showPhenotipsPDFModal ?
          <PhenotipsPDFModal
            projectId={projectId}
            phenotipsId={phenotipsId}
            individualId={individualId}
            hidePhenotipsPDFModal={this.hidePhenotipsPDFModal}
          /> :
          null
        }
      </div>

      {(phenotipsData && (phenotipsData.features || phenotipsData.rejectedGenes || phenotipsData.genes)) ?

        <div className={classNames.infoDiv} style={{ paddingTop: '10px', paddingBottom: '10px' }}>
          {
            phenotipsData.features ?
              do {
                const presentFeatures = phenotipsData.features
                  .filter((feature) => { return feature.observed === 'yes' })
                  .map(feature => feature.label).join(', ')
                if (presentFeatures) {
                  <div>
                    <b>Present: </b>
                    <div className={classNames.infoDiv}>
                      {presentFeatures}
                    </div>
                  </div>
                }
              } :
              null
          }
          {
            phenotipsData.features ?
              do {
                const absentFeatures = phenotipsData.features
                  .filter((feature) => { return feature.observed === 'no' })
                  .map(feature => feature.label).join(', ')
                if (absentFeatures) {
                  <div>
                    <b>Absent: </b>
                    <div className={classNames.infoDiv}>
                      {absentFeatures}
                    </div>
                  </div>
                }
              } :
              null
          }
          {
            phenotipsData.rejectedGenes ?
              <div>
                <b>Previously Tested Genes: </b>
                <div className={classNames.infoDiv}>
                  {
                    phenotipsData.rejectedGenes.map((gene, i) => {
                      return <div key={i}>{`${gene.gene} ${gene.comments ? `(${gene.comments.trim()})` : ''}`}</div>
                    })
                  }
                </div>
              </div> :
              null
          }
          {
            phenotipsData.genes ?
              <div>
                <b>Candidate Genes: </b>
                <div className={classNames.infoDiv}>
                  {
                    phenotipsData.genes.map((gene, i) => {
                      return <div key={i}>{`${gene.gene} (${gene.comments ? gene.comments.trim() : ''})`}</div>
                    })
                  }
                </div>
              </div> :
              null
          }
        </div>
        : null
      }
    </div>
  }
}

export default PhenotipsDataView

