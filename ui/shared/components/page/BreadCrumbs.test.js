import React from 'react'
import { shallow } from 'enzyme'
import BreadCrumbs from './BreadCrumbs'


test('shallow-render without crashing', () => {
  /*
    breadcrumbSections: PropTypes.array.isRequired,
   */

  const props = {
    breadcrumbSections: ['base', 'subsection', 'subsection2'],
  }

  shallow(<BreadCrumbs {...props} />)
})
