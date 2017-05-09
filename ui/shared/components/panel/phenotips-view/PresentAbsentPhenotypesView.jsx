import React from 'react'
import PropTypes from 'prop-types'

import CategorizedHPOTermsView from './CategorizedHPOTermsView'
import groupFeaturesByPresentAbsent from './utils'


const PresentAbsentPhenotypesView = ({ features }) => {
  const groupedHPOTerms = groupFeaturesByPresentAbsent(features)

  return <div>
    {
      Object.keys(groupedHPOTerms.yes).length ?
        <div>
          <b>Present:</b>
          <CategorizedHPOTermsView hpoTerms={groupedHPOTerms.yes} />
        </div> : null
    }
    {
      Object.keys(groupedHPOTerms.no).length ?
        <div>
          <b>Not Present:</b>
          <CategorizedHPOTermsView hpoTerms={groupedHPOTerms.no} />
        </div> : null
    }
  </div>
}

PresentAbsentPhenotypesView.propTypes = {
  features: PropTypes.array.isRequired,
}

export default PresentAbsentPhenotypesView
