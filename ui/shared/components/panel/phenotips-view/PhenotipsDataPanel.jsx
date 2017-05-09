/* eslint no-unused-expressions: 0 */

import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import { Icon, Popup } from 'semantic-ui-react'
import { HorizontalSpacer } from 'shared/components/Spacers'
import { showPhenotipsModal } from 'shared/components/panel/phenotips-modal/state'

import PresentAbsentPhenotypesView from './PresentAbsentPhenotypesView'


const infoDivStyle = {
  padding: '0px 0px 10px 20px',
}

class PhenotipsDataPanel extends React.Component
{
  static propTypes = {
    project: PropTypes.object.isRequired,
    individual: PropTypes.object.isRequired,
    showDetails: PropTypes.bool.isRequired,
    showPhenotipsModal: PropTypes.func.isRequired,
  }

  render() {
    const { project, individual, showDetails } = this.props
    const { phenotipsData } = individual

    return <div>
      <b>PhenoTips</b>

      <HorizontalSpacer width={15} />

      <div style={{ display: 'inline-block' }}>
        {
          individual.phenotipsPatientId ?
            <a tabIndex="0" onClick={() => this.props.showPhenotipsModal(project, individual)} style={{ cursor: 'pointer' }}>
              <Icon name="file pdf outline" title="PhenoTips PDF" />
            </a>
            : <Popup
              trigger={<Icon name="file pdf outline" title="PhenoTips PDF" />}
              content={<div>PhenoTips data not available for this individual.</div>}
              size="small"
            />
        }
      </div>
      {showDetails ?
        <div style={infoDivStyle}>
          {(phenotipsData && (phenotipsData.features || phenotipsData.rejectedGenes || phenotipsData.genes)) ?

            <div style={{ paddingTop: '10px', paddingBottom: '10px' }}>
              {
                phenotipsData.features ?
                  <PresentAbsentPhenotypesView features={phenotipsData.features} /> : null
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
                  </div> : null
              }
              {
                phenotipsData.genes ?
                  <div>
                    <b>Candidate Genes: </b>
                    <div style={infoDivStyle}>
                      {
                        phenotipsData.genes.map((gene, i) => {
                          return <div key={i}>{`${gene.gene} ${gene.comments ? `(${gene.comments.trim()})` : ''}`}</div>
                        })
                      }
                    </div>
                  </div> :
                  null
              }

              {
                phenotipsData.ethnicity && (phenotipsData.ethnicity.paternal_ethnicity.length || phenotipsData.ethnicity.maternal_ethnicity.length) ?

                  <div>
                    <b>Ancestry:</b><br />
                    <div style={infoDivStyle}>
                      {(() => {
                        const paternalAncestries = phenotipsData.ethnicity.paternal_ethnicity  //array
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

              {
                phenotipsData.global_age_of_onset ?
                  <div>
                    <b>Age of Onset:</b><br />
                    <div style={infoDivStyle}>
                      { phenotipsData.global_age_of_onset.map(s => s.label).join(', ') }
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

export { PhenotipsDataPanel as PhenotipsDataPanelComponent }

const mapDispatchToProps = dispatch => bindActionCreators({ showPhenotipsModal }, dispatch)

export default connect(null, mapDispatchToProps)(PhenotipsDataPanel)

