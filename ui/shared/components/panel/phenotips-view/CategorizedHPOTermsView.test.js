import React from 'react'
import { shallow } from 'enzyme'

import CategorizedHPOTermsView from './CategorizedHPOTermsView'
import groupFeaturesByPresentAbsent from './utils'

import { STATE1 } from '../fixtures'


test('shallow-render without crashing', () => {
  /*
   hpoTerms: PropTypes.object.isRequired,
   */

  const groupedHPOTerms = groupFeaturesByPresentAbsent(STATE1.individualsByGuid.I021474_na19679.phenotipsData.features)

  shallow(<CategorizedHPOTermsView hpoTerms={groupedHPOTerms.yes} />)
  shallow(<CategorizedHPOTermsView hpoTerms={groupedHPOTerms.no} />)
})
