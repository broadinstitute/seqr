/* eslint-disable no-unused-expressions */
/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'

import { HorizontalSpacer } from 'shared/components/Spacers'

import ShowPhenotipsModalButton from 'shared/components/buttons/ShowPhenotipsModalButton'
import PresentAbsentPhenotypesView from './PresentAbsentPhenotypesView'

const infoDivStyle = {
  padding: '0px 0px 10px 20px',
}

export const hasPhenotipsDetails = phenotipsData =>
  phenotipsData && (phenotipsData.features || phenotipsData.rejectedGenes || phenotipsData.genes)

const PhenotipsSection = ({ phenotipsData, field, formatFieldRow, title, join }) => {
  const fieldData = phenotipsData[field]
  if (!fieldData || fieldData.length < 1) {
    return null
  }
  return (
    <div>
      <b>{title}:</b>
      <div style={infoDivStyle}>
        {
          join ? fieldData.map(row => formatFieldRow(row)).join(join) : fieldData.map((row, i) => {
            return <div key={i}>{formatFieldRow(row)}</div>
          })
        }
      </div>
    </div>
  )
}

PhenotipsSection.propTypes = {
  phenotipsData: PropTypes.object,
  field: PropTypes.string,
  formatFieldRow: PropTypes.func,
  title: PropTypes.string,
  join: PropTypes.string,
}


class PhenotipsDataPanel extends React.Component
{
  static propTypes = {
    individual: PropTypes.object.isRequired,
    showDetails: PropTypes.bool.isRequired,
    showEditPhenotipsLink: PropTypes.bool.isRequired,
    showViewPhenotipsLink: PropTypes.bool,
  }

  render() {
    const { individual, showDetails, showEditPhenotipsLink, showViewPhenotipsLink = true } = this.props
    const { phenotipsData } = individual

    return (
      <div>
        <b>PhenoTips{(showDetails && hasPhenotipsDetails(phenotipsData)) ? ':' : ''}</b><HorizontalSpacer width={15} />
        { showViewPhenotipsLink && <ShowPhenotipsModalButton individual={individual} isViewOnly /> }
        {
          showEditPhenotipsLink && [
            <HorizontalSpacer key={1} width={10} />,
            <ShowPhenotipsModalButton key={2} individual={individual} isViewOnly={false} />,
          ]
        }
        {showDetails ?
          <div style={infoDivStyle}>
            {phenotipsData && hasPhenotipsDetails(phenotipsData) &&
              <div style={{ paddingTop: '10px', paddingBottom: '10px' }}>
                {
                  phenotipsData.features ?
                    <PresentAbsentPhenotypesView features={phenotipsData.features} /> : null
                }
                <PhenotipsSection
                  phenotipsData={phenotipsData}
                  field="rejectedGenes"
                  title="Previously Tested Genes"
                  formatFieldRow={gene => `${gene.gene} ${gene.comments ? `(${gene.comments.trim()})` : ''}`}
                />
                <PhenotipsSection
                  phenotipsData={phenotipsData}
                  field="genes"
                  title="Candidate Genes"
                  formatFieldRow={gene => `${gene.gene} ${gene.comments ? `(${gene.comments.trim()})` : ''}`}
                />
                {
                  phenotipsData.ethnicity && (phenotipsData.ethnicity.paternal_ethnicity.length || phenotipsData.ethnicity.maternal_ethnicity.length) ?
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
                <PhenotipsSection
                  phenotipsData={phenotipsData}
                  field="global_age_of_onset"
                  title="Age of Onset"
                  formatFieldRow={s => s.label}
                  join=", "
                />
              </div>
            }
          </div> :
          <div style={{ display: 'inline-block', paddingBottom: '15px', color: 'gray' }}>
            <HorizontalSpacer width={30} />
            {(phenotipsData && phenotipsData.features) ? `${phenotipsData.features.length} phenotype terms` : null} &nbsp;
            {(phenotipsData && phenotipsData.rejectedGenes) ? `${phenotipsData.rejectedGenes.length} previously tested genes` : null} &nbsp;
            {(phenotipsData && phenotipsData.genes) ? `${phenotipsData.genes.length} candidate genes` : null}
          </div>
        }
      </div>)
  }
}

export { PhenotipsDataPanel as PhenotipsDataPanelComponent }

export default PhenotipsDataPanel

//const mapDispatchToProps = dispatch => bindActionCreators({ showPhenotipsModal }, dispatch)
//export default connect(null, mapDispatchToProps)(PhenotipsDataPanel)
