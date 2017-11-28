import React from 'react'
import PropTypes from 'prop-types'
import { getNameForCategoryHpoId } from '../../../utils/hpoUtils'


const infoDivStyle = {
  padding: '0px 0px 10px 20px',
}


const CategorizedHPOTermsView = ({ hpoTerms }) => {
  const categoryHpoIds = Object.keys(hpoTerms).sort(
    (a, b) => getNameForCategoryHpoId(a).localeCompare(getNameForCategoryHpoId(b)),
  )

  return (
    <div style={infoDivStyle}>
      {
        categoryHpoIds.length ?
          categoryHpoIds.map(
            categoryHpoId =>
              <div key={categoryHpoId}>
                <b>{getNameForCategoryHpoId(categoryHpoId)}</b>: {
                  (hpoTerms[categoryHpoId] || []).map(
                    hpoTerm => (hpoTerm.notes ? `${hpoTerm.label} (${hpoTerm.notes})` : hpoTerm.label),
                  ).join(', ')
                }
              </div>)
        : null
      }
    </div>)
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
