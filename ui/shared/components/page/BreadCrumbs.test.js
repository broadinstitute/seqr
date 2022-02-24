import React from 'react'
import { shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import BreadCrumbs from './BreadCrumbs'

configure({ adapter: new Adapter() })

test('shallow-render without crashing', () => {
  /*
    breadcrumbSections: PropTypes.array.isRequired,
   */

  const props = {
    breadcrumbSections: ['base', 'subsection', 'subsection2'],
  }

  shallow(<BreadCrumbs {...props} />)
})
