import React from 'react'
import { shallow } from 'enzyme'
import { PhenotipsDataViewComponent } from './PhenotipsDataView'
import { getProject, getIndividualsByGuid } from '../../../reducers/rootReducer'

import { STATE1 } from '../../../fixtures'


test('shallow-render without crashing', () => {
  /*
    hpoTerms: React.PropTypes.object.isRequired,    features: React.PropTypes.array.isRequired,    project: React.PropTypes.object.isRequired,
    individual: React.PropTypes.object.isRequired,
    showDetails: React.PropTypes.bool.isRequired,
    showViewPhenotipsModal: React.PropTypes.func.isRequired,
   */

  const props = {
    project: getProject(STATE1),
    individual: getIndividualsByGuid(STATE1).I021474_na19679,
    showDetails: true,
    showViewPhenotipsModal: () => {},
  }

  shallow(<PhenotipsDataViewComponent {...props} />)

  const props2 = { ...props, showDetails: false }

  shallow(<PhenotipsDataViewComponent {...props2} />)
})
