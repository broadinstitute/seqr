/* eslint no-unused-expressions: 0 */

import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import { Icon, Popup } from 'semantic-ui-react'
import { getProject, showViewPhenotipsModal } from '../../../reducers/rootReducer'

import { HorizontalSpacer } from '../../../../../shared/components/Spacers'

const infoDivStyle = {
  padding: '0px 0px 10px 20px',
}

const UNKNOWN_CATEGORY = 'Other'
const CATEGORY_NAMES = {
  'HP:0000119': 'Genitourinary System',
  'HP:0000152': 'Head or Neck',
  'HP:0000478': 'Eye Defects',
  'HP:0000598': 'Ear Defects',
  'HP:0000707': 'Nervous System',
  'HP:0000769': 'Breast',
  'HP:0000818': 'Endocrine System',
  'HP:0000924': 'Skeletal System',
  'HP:0001197': 'Prenatal development or birth',
  'HP:0001507': 'Growth Abnormality',
  'HP:0001574': 'Integument',
  'HP:0001608': 'Voice',
  'HP:0001626': 'Cardiovascular System',
  'HP:0001871': 'Blood',
  'HP:0001939': 'Metabolism/Homeostasis',
  'HP:0002086': 'Respiratory',
  'HP:0002664': 'Neoplasm',
  'HP:0002715': 'Immune System',
  'HP:0003011': 'Musculature',
  'HP:0003549': 'Connective Tissue',
  'HP:0025031': 'Digestive System',
  'HP:0040064': 'Limbs',
  'HP:0045027': 'Thoracic Cavity',
}


const HPOTermsInCategories = ({ hpoTerms }) => {
  const categories = Object.keys(hpoTerms).sort(
    (a, b) => (CATEGORY_NAMES[a] || UNKNOWN_CATEGORY).localeCompare((CATEGORY_NAMES[b] || UNKNOWN_CATEGORY)))

  return <div style={infoDivStyle}>
    {
      categories.length ?
        categories.map(
          category => <div key={category}>
            <b>{CATEGORY_NAMES[category] || UNKNOWN_CATEGORY}</b>: {hpoTerms[category].join(', ')}
          </div>,
        ) : null
    }
  </div>
}

export { HPOTermsInCategories as HPOTermsInCategoriesComponent }

HPOTermsInCategories.propTypes = {
  hpoTerms: React.PropTypes.object.isRequired,
}


const PresentAndAbsentPhenotypes = ({ features }) => {
  const hpoTermsByCategory = {
    yes: {},
    no: {},
  }
  features.forEach((hpoTerm) => {
    const d = hpoTermsByCategory[hpoTerm.observed]
    if (!d[hpoTerm.category]) {
      d[hpoTerm.category] = []  // init array of features
    }
    d[hpoTerm.category].push(hpoTerm.label)
  })

  return <div>
    {
      Object.keys(hpoTermsByCategory.yes).length ?
        <div>
          <b>Present:</b>
          <HPOTermsInCategories hpoTerms={hpoTermsByCategory.yes} />
        </div> : null
    }
    {
      Object.keys(hpoTermsByCategory.no).length ?
        <div>
          <b>Not Present:</b>
          <HPOTermsInCategories hpoTerms={hpoTermsByCategory.no} />
        </div> : null
    }
  </div>
}

export { PresentAndAbsentPhenotypes as PresentAndAbsentPhenotypesComponent }

PresentAndAbsentPhenotypes.propTypes = {
  features: React.PropTypes.array.isRequired,
}

class PhenotipsDataView extends React.Component
{
  static propTypes = {
    project: React.PropTypes.object.isRequired,
    individual: React.PropTypes.object.isRequired,
    showDetails: React.PropTypes.bool.isRequired,
    showViewPhenotipsModal: React.PropTypes.func.isRequired,
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
            <a tabIndex="0" onClick={() => this.props.showViewPhenotipsModal(project, individual)} style={{ cursor: 'pointer' }}>
              <Icon name="file pdf outline" title="PhenoTips PDF" />
            </a> :
            <Popup trigger={<Icon name="file pdf outline" title="PhenoTips PDF" />} content={<div>PhenoTips data not available for this individual.</div>} size="small" />
        }
      </div>
      {showDetails ?
        <div style={infoDivStyle}>
          {(phenotipsData && (phenotipsData.features || phenotipsData.rejectedGenes || phenotipsData.genes)) ?

            <div style={{ paddingTop: '10px', paddingBottom: '10px' }}>
              {
                phenotipsData.features ?
                  <PresentAndAbsentPhenotypes features={phenotipsData.features} /> : null
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

export { PhenotipsDataView as PhenotipsDataViewComponent }

const mapStateToProps = state => ({
  project: getProject(state),
})

const mapDispatchToProps = dispatch => bindActionCreators({ showViewPhenotipsModal }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(PhenotipsDataView)

