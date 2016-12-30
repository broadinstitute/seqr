/* eslint no-unused-expressions: 0 */

import React from 'react'
import { Icon } from 'semantic-ui-react'

import { HorizontalSpacer } from '../../../shared/components/Spacers'
import PhenotipsPDFModal from './PhenotipsPDFModal'


const infoDivStyle = {
  paddingLeft: '20px',
}


class PhenotipsDataView extends React.Component
{

  static propTypes = {
    projectId: React.PropTypes.string.isRequired,
    individualId: React.PropTypes.string.isRequired,
    phenotipsId: React.PropTypes.string.isRequired,
    phenotipsData: React.PropTypes.object,
    showDetails: React.PropTypes.bool.isRequired,
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
    const { projectId, individualId, phenotipsId, phenotipsData, showDetails } = this.props

    return <div>
      <b>PhenoTips</b>

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
      {showDetails ?
        <div style={infoDivStyle}>
          {(phenotipsData && (phenotipsData.features || phenotipsData.rejectedGenes || phenotipsData.genes)) ?

            <div style={{ paddingTop: '10px', paddingBottom: '10px' }}>
              {
                phenotipsData.features ?
                  (() => {
                    const presentFeatures = phenotipsData.features
                      .filter((feature) => { return feature.observed === 'yes' })
                      .map(feature => feature.label).join(', ')
                    if (presentFeatures) {
                      <div>
                        <b>Present: </b>
                        <div style={infoDivStyle}>
                          {presentFeatures}
                        </div>
                      </div>
                    }
                  })() :
                  null
              }
              {
                phenotipsData.features ?
                  (() => {
                    const absentFeatures = phenotipsData.features
                      .filter((feature) => { return feature.observed === 'no' })
                      .map(feature => feature.label).join(', ')
                    if (absentFeatures) {
                      <div>
                        <b>Absent: </b>
                        <div style={infoDivStyle}>
                          {absentFeatures}
                        </div>
                      </div>
                    }
                  })() :
                  null
              }
              {
                phenotipsData.rejectedGenes ?
                  <div>
                    <b>Previously Tested Genes: </b>
                    <div style={infoDivStyle}>
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
                    <div style={infoDivStyle}>
                      {
                        phenotipsData.genes.map((gene, i) => {
                          return <div key={i}>{`${gene.gene} (${gene.comments ? gene.comments.trim() : ''})`}</div>
                        })
                      }
                    </div>
                  </div> :
                  null
              }
              { console.log('ethnicity', phenotipsData) }
              {
                phenotipsData.ethnicity && (phenotipsData.ethnicity.paternal_ethnicity || phenotipsData.ethnicity.maternal_ethnicity) ?
                  <div>
                    <b>Ancestry:</b><br />
                    <div style={infoDivStyle}>
                      {(() => {
                        const paternalAncestries = phenotipsData.ethnicity.paternal_ethnicity //array
                        const maternalAncestries = phenotipsData.ethnicity.maternal_ethnicity
                        if (!paternalAncestries.length && !maternalAncestries.length) {
                          return ''
                        }
                        return (
                          (paternalAncestries.length ? `father is ${paternalAncestries.join(' / ')}` : '') +
                          (paternalAncestries.length && maternalAncestries.length ? ', ' : '') +
                          (maternalAncestries.length ? `mother is ${maternalAncestries.join(' / ')}` : '')
                        )
                      })()}
                    </div>
                  </div>
                  : null
              }
            </div>
            : null
          }
        </div> :
        <div style={{ display: 'inline', color: 'gray' }}>
          <HorizontalSpacer width={30} />
          {(phenotipsData && phenotipsData.features) ? `${phenotipsData.features.length} phenotype terms` : null} &nbsp;
          {(phenotipsData && phenotipsData.rejectedGenes) ? `${phenotipsData.rejectedGenes.length} previously tested genes` : null} &nbsp;
          {(phenotipsData && phenotipsData.genes) ? `${phenotipsData.genes.length} candidate genes` : null}
        </div>
      }
    </div>
  }
}

export default PhenotipsDataView

