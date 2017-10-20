import React from 'react'
import PropTypes from 'prop-types'

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


const infoDivStyle = {
  padding: '0px 0px 10px 20px',
}


const CategorizedHPOTermsView = ({ hpoTerms }) => {
  const categories = Object.keys(hpoTerms).sort(
    (a, b) => (CATEGORY_NAMES[a] || UNKNOWN_CATEGORY).localeCompare((CATEGORY_NAMES[b] || UNKNOWN_CATEGORY)),
  )

  return <div style={infoDivStyle}>
    {
      categories.length ?
        categories.map(
          category =>
            <div key={category}>
              <b>{CATEGORY_NAMES[category] || UNKNOWN_CATEGORY}</b>:
              {
                (hpoTerms[category] || []).map(
                  hpoTerm => (hpoTerm.notes ? `${hpoTerm.label} (${hpoTerm.notes})` : hpoTerm.label),
                ).join(', ')
              }
            </div>)
      : null
    }
  </div>
}

CategorizedHPOTermsView.propTypes = {
  /**
   * A dictionary of HPO terms by category, for example:
   *
   * hpoTerms = {
   *  'HP:0001507': [ 'Childhood onset short-limb short stature', 'Decreased body weight' ],
   *  'HP:0040064': [ 'Forearm undergrowth' ],
   *  'HP:0003011': [ 'Generalized hypotonia' ],
   *  'HP:0000707': [ 'Seizures' ],
   *  'HP:0000924': [ 'Skeletal dysplasia' ]
   *  },
   */
  hpoTerms: PropTypes.object.isRequired,
}

export default CategorizedHPOTermsView
