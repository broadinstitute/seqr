import React from 'react'
import { shallow } from 'enzyme'
import { CaseReviewLinkComponent } from './CaseReviewLink'

test('shallow-render without crashing', () => {
  /*
    projectGuid: React.PropTypes.string.isRequired,
   */

  const props = {
    projectGuid: 'R0237_1000_genomes_demo',
  }

  shallow(<CaseReviewLinkComponent {...props} />)
})
