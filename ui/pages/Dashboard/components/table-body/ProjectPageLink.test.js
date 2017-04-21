import React from 'react'
import { shallow } from 'enzyme'
import { ProjectPageLinkComponent } from './ProjectPageLink'


test('shallow-render without crashing', () => {
  /*
    project: React.PropTypes.object.isRequired,
   */

  const props = {
    project: { deprecatedProjectId: '1' },
  }

  shallow(<ProjectPageLinkComponent {...props} />)
})
