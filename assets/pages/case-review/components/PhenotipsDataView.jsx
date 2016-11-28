/* eslint no-unused-expressions: 0 */

import React from 'react'
import injectSheet from 'react-jss'


const styles = {
  infoDiv: {
    paddingLeft: '20px',
  },
}


@injectSheet(styles)
class PhenotipsDataView extends React.Component
{

  static propTypes = {
    phenotipsData: React.PropTypes.object.isRequired,
    sheet: React.PropTypes.object,
  }

  render() {
    const classNames = this.props.sheet.classes

    return <div>
      <b>PhenoTips:</b>
      <div className={classNames.infoDiv}>
        {
          do {
            const presentFeatures = this.props.phenotipsData.features
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
          }
        }
        {
          do {
            const absentFeatures = this.props.phenotipsData.features
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
          }
        }
        {
          this.props.phenotipsData.rejectedGenes ?
            <div>
              <b>Previously Tested Genes: </b>
              <div className={classNames.infoDiv}>
                {
                  this.props.phenotipsData.rejectedGenes.map((gene, i) => {
                    return <div key={i}>{`${gene.gene} ${gene.comments ? `(${gene.comments.trim()})` : ''}`}</div>
                  })
                }
              </div>
            </div> :
            null
        }
        {
          this.props.phenotipsData.genes ?
            <div>
              <b>Candidate Genes: </b>
              <div className={classNames.infoDiv}>
                {
                  this.props.phenotipsData.genes.map((gene, i) => {
                    return <div key={i}>{`${gene.gene} (${gene.comments ? gene.comments.trim() : ''})`}</div>
                  })
                }
              </div>
            </div> :
            null
        }
      </div>
    </div>
  }
}

export default PhenotipsDataView

