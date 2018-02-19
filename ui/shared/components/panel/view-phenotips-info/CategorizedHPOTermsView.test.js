import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from 'enzyme-adapter-react-16'

import CategorizedHPOTermsView from './CategorizedHPOTermsView'
import groupFeaturesByPresentAbsent from './utils'

import { STATE1 } from '../fixtures'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
   hpoTerms: PropTypes.object.isRequired,
   */

  const groupedHPOTerms = groupFeaturesByPresentAbsent(STATE1.individualsByGuid.I021474_na19679.phenotipsData.features)

  shallow(<CategorizedHPOTermsView hpoTerms={groupedHPOTerms.yes} />)
  shallow(<CategorizedHPOTermsView hpoTerms={groupedHPOTerms.no} />)
})
